# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# Quotation Comparison server-side functions.

import frappe
import json
from frappe import _
from frappe.utils import nowdate, now_datetime, add_months, flt


@frappe.whitelist()
def create_from_rfq(rfq_name):
    """Create a new PEPL Quotation Comparison from a
    submitted RFQ. Returns the name of the new or existing
    comparison doc. Idempotent — returns existing if any
    non-cancelled Comparison already exists for this RFQ."""
    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    if rfq.docstatus != 1:
        frappe.throw(
            _("RFQ {0} is not submitted (docstatus={1}).").format(
                rfq_name, rfq.docstatus
            ),
            frappe.ValidationError,
        )

    existing = frappe.db.get_value(
        "PEPL Quotation Comparison",
        {
            "linked_rfq": rfq_name,
            "status": ["in", ["Draft", "Pending Approval", "Approved"]],
        },
        "name",
    )
    if existing:
        return existing

    comparison = frappe.new_doc("PEPL Quotation Comparison")
    comparison.linked_rfq = rfq_name
    comparison.comparison_date = nowdate()
    comparison.status = "Draft"

    # Populate one comparison_item row per RFQ item.
    # required_qty = RFQ qty (read-only ground truth).
    # qty (= allocated_qty) defaults to required_qty for the
    # single-vendor case. User can split by adding more rows
    # via the Phase 2b UI.
    for rfq_item in (rfq.items or []):
        comparison.append("comparison_items", {
            "item_code": rfq_item.item_code,
            "item_name": rfq_item.item_name,
            "required_qty": flt(rfq_item.qty),
            "qty": flt(rfq_item.qty),
            "uom": rfq_item.uom,
            "required_by": getattr(rfq_item, "schedule_date", None),
        })

    # Build vendor_responses from current SQ state
    for resp in _build_responses_from_sql(rfq_name):
        comparison.append("vendor_responses", resp)

    comparison.insert(ignore_permissions=True)
    frappe.db.commit()

    return comparison.name


@frappe.whitelist()
def get_rate_history(item_code, months=24, vendor=None):
    """
    Last `months` months of price history for an item, optionally
    filtered to a specific vendor. Combines Supplier Quotations
    and Purchase Orders. Returns list of dicts sorted date desc.
    """
    months = int(months)
    cutoff_date = add_months(nowdate(), -months)

    sq_rows = frappe.db.sql(
        """
        SELECT
            sq.transaction_date  AS `date`,
            sq.supplier          AS vendor,
            sqi.rate             AS rate,
            'SQ'                 AS source,
            sq.name              AS reference
        FROM `tabSupplier Quotation Item` sqi
        JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
        WHERE sq.docstatus = 1
          AND sq.transaction_date >= %(cutoff)s
          AND sqi.item_code = %(item_code)s
          AND (%(vendor)s IS NULL OR sq.supplier = %(vendor)s)
        """,
        {"cutoff": cutoff_date, "item_code": item_code, "vendor": vendor},
        as_dict=True,
    )

    po_rows = frappe.db.sql(
        """
        SELECT
            po.transaction_date  AS `date`,
            po.supplier          AS vendor,
            poi.rate             AS rate,
            'PO'                 AS source,
            po.name              AS reference
        FROM `tabPurchase Order Item` poi
        JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE po.docstatus = 1
          AND po.transaction_date >= %(cutoff)s
          AND poi.item_code = %(item_code)s
          AND (%(vendor)s IS NULL OR po.supplier = %(vendor)s)
        """,
        {"cutoff": cutoff_date, "item_code": item_code, "vendor": vendor},
        as_dict=True,
    )

    combined = list(sq_rows) + list(po_rows)
    combined.sort(key=lambda x: str(x.get("date") or ""), reverse=True)

    return [
        {
            "date": str(r["date"]) if r.get("date") else None,
            "vendor": r["vendor"],
            "rate": flt(r["rate"]),
            "source": r["source"],
            "reference": r["reference"],
        }
        for r in combined
    ]


@frappe.whitelist()
def approve_comparison(comparison_name):
    """Purchase Officer approval. Validates rate overrides and
    qty allocations. Auto-creates one draft PO per selected_vendor."""
    comparison = frappe.get_doc("PEPL Quotation Comparison", comparison_name)

    # Permission check
    user_roles = frappe.get_roles(frappe.session.user)
    if not any(r in user_roles for r in ("Purchase Manager", "System Manager")):
        frappe.throw(_("Only Purchase Manager can approve a Quotation Comparison."))

    if comparison.status in ("Approved", "Cancelled"):
        frappe.throw(
            _("Comparison {0} is already {1}.").format(
                comparison_name, comparison.status
            )
        )

    # Filter to rows that have been allocated (selected_vendor + qty > 0)
    allocated_rows = [
        row for row in (comparison.comparison_items or [])
        if row.selected_vendor and flt(row.qty) > 0
    ]
    if not allocated_rows:
        frappe.throw(_("No items have been allocated to any vendor."))

    # Validate selected_rate set on all allocated rows
    incomplete = [
        row.item_code or f"Row {row.idx}"
        for row in allocated_rows
        if not row.selected_rate
    ]
    if incomplete:
        frappe.throw(
            _("Selected Rate is required for: {0}").format(", ".join(incomplete))
        )

    # Validate rate override reasons
    rate_override_missing = [
        row.item_code or f"Row {row.idx}"
        for row in allocated_rows
        if flt(row.original_quoted_rate)
        and abs(flt(row.selected_rate) - flt(row.original_quoted_rate)) > 0.01
        and not row.override_reason
    ]
    if rate_override_missing:
        frappe.throw(
            _("Rate Override Reason required for: {0}").format(
                ", ".join(rate_override_missing)
            )
        )

    # Validate qty allocations sum to required_qty per item
    from collections import defaultdict
    allocated_sum = defaultdict(float)
    required_per_item = {}
    for row in (comparison.comparison_items or []):
        if row.required_qty:
            required_per_item[row.item_code] = flt(row.required_qty)
        if row.selected_vendor and row.qty:
            allocated_sum[row.item_code] += flt(row.qty)

    override_entries = json.loads(comparison.override_log or "[]")
    qty_override_items = {
        e.get("item_code") for e in override_entries
        if e.get("type") == "qty_override"
    }

    qty_mismatches = []
    for item_code, required in required_per_item.items():
        allocated = allocated_sum.get(item_code, 0)
        if abs(allocated - required) > 0.01 and item_code not in qty_override_items:
            qty_mismatches.append((item_code, required, allocated))

    if qty_mismatches:
        msg_lines = [_("Qty allocation does not match required for these items:")]
        for ic, req, alloc in qty_mismatches:
            msg_lines.append(f"  {ic}: required {req}, allocated {alloc}")
        msg_lines.append(_("Enter qty override reason via the form or fix allocations."))
        frappe.throw("\n".join(msg_lines))

    # Group allocated rows by vendor → one PO per vendor
    vendor_items = defaultdict(list)
    for row in allocated_rows:
        vendor_items[row.selected_vendor].append(row)

    today = nowdate()
    po_names = []

    for vendor, items in vendor_items.items():
        required_dates = [str(row.required_by) for row in items if row.required_by]
        schedule_date = max(required_dates) if required_dates else add_months(today, 1)

        po = frappe.new_doc("Purchase Order")
        po.supplier = vendor
        po.transaction_date = today
        po.schedule_date = schedule_date
        po.linked_quotation_comparison = comparison_name

        for row in items:
            po.append("items", {
                "item_code": row.item_code,
                "qty": flt(row.qty),
                "rate": flt(row.selected_rate),
                "schedule_date": row.required_by or schedule_date,
            })

        po.insert(ignore_permissions=True)
        po_names.append(po.name)

        # Append rate override entries to audit log
        for row in items:
            orig = flt(row.original_quoted_rate)
            sel = flt(row.selected_rate)
            if orig and abs(sel - orig) > 0.01:
                override_entries.append({
                    "type": "rate_override",
                    "item_code": row.item_code,
                    "vendor": vendor,
                    "old_rate": orig,
                    "new_rate": sel,
                    "reason": row.override_reason or "",
                    "user": frappe.session.user,
                    "ts": str(now_datetime()),
                })

    # Finalize comparison
    comparison.status = "Approved"
    comparison.approved_by = frappe.session.user
    comparison.approved_on = now_datetime()
    comparison.generated_pos = ",".join(po_names)
    comparison.override_log = json.dumps(override_entries, default=str)
    comparison.save(ignore_permissions=True)
    frappe.db.commit()

    # Generate PDF snapshot (best-effort; failure does not roll back)
    _generate_pdf_snapshot(comparison_name)

    return po_names


def _build_responses_from_sql(rfq_name):
    """Internal helper: query SQ items linked to RFQ, return
    list of response dicts ranked per item (1 = lowest rate)."""
    sq_item_rows = frappe.db.sql(
        """
        SELECT
            sqi.item_code           AS item_code,
            sqi.rate                AS rate,
            sqi.lead_time_days      AS lead_time_days,
            sqi.parent              AS sq_name,
            sq.supplier             AS vendor,
            sq.terms                AS terms
        FROM `tabSupplier Quotation Item` sqi
        JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
        WHERE sqi.request_for_quotation = %(rfq)s
          AND sq.docstatus = 1
        """,
        {"rfq": rfq_name},
        as_dict=True,
    )

    responses = []
    for r in sq_item_rows:
        responses.append({
            "item_code": r["item_code"],
            "vendor": r["vendor"],
            "supplier_quotation": r["sq_name"],
            "quoted_rate": flt(r["rate"]),
            "lead_time_days": int(r["lead_time_days"] or 0),
            "terms": r["terms"] or "",
        })

    from collections import defaultdict
    by_item = defaultdict(list)
    for r in responses:
        by_item[r["item_code"]].append(r)

    ranked = []
    for item_code, rows in by_item.items():
        rows_sorted = sorted(rows, key=lambda x: x["quoted_rate"])
        for rank, row in enumerate(rows_sorted, start=1):
            row["ranking"] = rank
            ranked.append(row)
    return ranked


@frappe.whitelist()
def sync_responses(comparison_name):
    """Refresh vendor_responses on an existing Comparison.
    Skips if Approved or Cancelled."""
    comparison = frappe.get_doc("PEPL Quotation Comparison", comparison_name)
    if comparison.status in ("Approved", "Cancelled"):
        return {"status": "skipped", "reason": f"Comparison is {comparison.status}"}

    responses = _build_responses_from_sql(comparison.linked_rfq)
    comparison.set("vendor_responses", [])
    for resp in responses:
        comparison.append("vendor_responses", resp)
    comparison.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "refreshed", "response_count": len(responses)}


@frappe.whitelist()
def get_comparison_data(comparison_name, months=24):
    """
    Rich payload for the Phase 2b grid UI. Returns per-item,
    per-vendor data including:
      - current_quote (None if vendor didn't quote in this RFQ)
      - history (last `months` months of rates from SQ + PO)
    Includes vendors who have history for an item but didn't
    quote in this RFQ (current_quote = None).
    """
    months = int(months)
    comparison = frappe.get_doc("PEPL Quotation Comparison", comparison_name)

    # Build current quotes index: {item_code: {vendor: response_dict}}
    current_quotes = {}
    for resp in (comparison.vendor_responses or []):
        current_quotes.setdefault(resp.item_code, {})[resp.vendor] = {
            "rate": flt(resp.quoted_rate),
            "lead_time_days": int(resp.lead_time_days or 0),
            "supplier_quotation": resp.supplier_quotation,
            "ranking": int(resp.ranking or 0),
            "terms": resp.terms or "",
        }

    # For each comparison_item's item_code, build per-vendor view
    result = {}
    seen_items = set()
    for ci in (comparison.comparison_items or []):
        if ci.item_code in seen_items:
            continue
        seen_items.add(ci.item_code)

        # All vendors with history for this item (any vendor, last N months)
        history_all = get_rate_history(ci.item_code, months=months)
        vendors_with_history = {h["vendor"] for h in history_all}
        vendors_who_quoted = set(current_quotes.get(ci.item_code, {}).keys())
        all_vendors = vendors_who_quoted | vendors_with_history

        vendor_data = {}
        for v in all_vendors:
            vendor_history = [h for h in history_all if h["vendor"] == v]
            vendor_data[v] = {
                "current_quote": current_quotes.get(ci.item_code, {}).get(v),
                "history": vendor_history,
            }

        result[ci.item_code] = {
            "item_name": ci.item_name,
            "required_qty": flt(ci.required_qty),
            "uom": ci.uom,
            "required_by": str(ci.required_by) if ci.required_by else None,
            "vendors": vendor_data,
        }

    return result


@frappe.whitelist()
def record_qty_override(comparison_name, item_code, reason):
    """Record (or update) a qty override reason for an item
    in the override_log. Called by Phase 2b UI when user enters
    a reason for qty allocation mismatch."""
    if not reason or not reason.strip():
        frappe.throw(_("Reason cannot be blank."))

    comparison = frappe.get_doc("PEPL Quotation Comparison", comparison_name)
    if comparison.status in ("Approved", "Cancelled"):
        frappe.throw(_("Cannot modify {0} Comparison.").format(comparison.status))

    log = json.loads(comparison.override_log or "[]")
    # Remove any prior qty_override for this item
    log = [
        e for e in log
        if not (e.get("type") == "qty_override" and e.get("item_code") == item_code)
    ]
    log.append({
        "type": "qty_override",
        "item_code": item_code,
        "reason": reason.strip(),
        "user": frappe.session.user,
        "ts": str(now_datetime()),
    })
    comparison.override_log = json.dumps(log, default=str)
    comparison.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "recorded"}


def auto_create_on_rfq_submit(doc, method):
    """doc_events hook: auto-create Comparison on RFQ submit."""
    try:
        create_from_rfq(doc.name)
    except Exception as e:
        frappe.log_error(
            f"auto_create_on_rfq_submit failed for {doc.name}: {e}",
            "Quotation Comparison Hook",
        )


def auto_refresh_on_sq_submit(doc, method):
    """doc_events hook: refresh Comparison when a linked SQ submits."""
    try:
        rfq_names = set()
        for item in (doc.items or []):
            if getattr(item, "request_for_quotation", None):
                rfq_names.add(item.request_for_quotation)

        if not rfq_names:
            return

        for rfq_name in rfq_names:
            comparison_name = frappe.db.get_value(
                "PEPL Quotation Comparison",
                {
                    "linked_rfq": rfq_name,
                    "status": ["in", ["Draft", "Pending Approval"]],
                },
                "name",
            )
            if comparison_name:
                sync_responses(comparison_name)
            else:
                create_from_rfq(rfq_name)
    except Exception as e:
        frappe.log_error(
            f"auto_refresh_on_sq_submit failed for SQ {doc.name}: {e}",
            "Quotation Comparison Hook",
        )


def _generate_pdf_snapshot(comparison_name):
    """Generate PDF snapshot via the Print Format and attach to
    the Comparison record. Called at end of approve_comparison.
    Wrapped in try/except — failure here must NOT roll back approval."""
    try:
        from frappe.utils.pdf import get_pdf

        html = frappe.get_print(
            doctype="PEPL Quotation Comparison",
            name=comparison_name,
            print_format="PEPL Quotation Comparison Snapshot",
        )
        pdf_content = get_pdf(html)

        ts = now_datetime().strftime("%Y%m%d_%H%M%S")
        file_name = f"{comparison_name}_snapshot_{ts}.pdf"

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "content": pdf_content,
            "attached_to_doctype": "PEPL Quotation Comparison",
            "attached_to_name": comparison_name,
            "is_private": 1,
        })
        file_doc.insert(ignore_permissions=True)

        # Update pdf_snapshot field via raw set_value to avoid re-running
        # validate on the parent (it's already Approved/frozen)
        frappe.db.set_value(
            "PEPL Quotation Comparison",
            comparison_name,
            "pdf_snapshot",
            file_doc.file_url,
        )
        frappe.db.commit()
        return file_doc.file_url
    except Exception as e:
        frappe.log_error(
            f"_generate_pdf_snapshot failed for {comparison_name}: {e}",
            "Quotation Comparison PDF Snapshot",
        )
        return None
