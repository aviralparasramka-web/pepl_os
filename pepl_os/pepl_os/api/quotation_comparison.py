# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# Quotation Comparison server-side functions.

import frappe
import json
from frappe import _
from frappe.utils import nowdate, now_datetime, add_months, flt


@frappe.whitelist()
def create_from_rfq(rfq_name):
    """
    Create a new PEPL Quotation Comparison record from an
    existing submitted RFQ.

    Returns the name of the (new or existing) comparison doc.
    """
    # 1. Validate RFQ
    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    if rfq.docstatus != 1:
        frappe.throw(
            _("RFQ {0} is not submitted (docstatus={1}). Submit it first.").format(
                rfq_name, rfq.docstatus
            ),
            frappe.ValidationError,
        )

    # 2. Check for existing non-cancelled comparison for this RFQ
    existing = frappe.db.get_value(
        "PEPL Quotation Comparison",
        {"linked_rfq": rfq_name, "status": ["in", ["Draft", "Pending Approval", "Approved"]]},
        "name",
    )
    if existing:
        return existing

    # 3. Find all submitted Supplier Quotation Items linked to
    #    this RFQ. ERPNext stores the RFQ linkage on the SQ Item
    #    child (sqi.request_for_quotation), NOT on the SQ parent.
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

    # 4. Build new comparison doc
    comparison = frappe.new_doc("PEPL Quotation Comparison")
    comparison.linked_rfq = rfq_name
    comparison.comparison_date = nowdate()
    comparison.status = "Draft"

    # 5. Populate comparison_items from RFQ items
    #    (ERPNext RFQ Item uses schedule_date for required-by)
    for rfq_item in (rfq.items or []):
        comparison.append("comparison_items", {
            "item_code": rfq_item.item_code,
            "item_name": rfq_item.item_name,
            "qty": flt(rfq_item.qty),
            "uom": rfq_item.uom,
            "required_by": getattr(rfq_item, "schedule_date", None),
        })

    # 6. Build vendor_responses directly from the SQL result
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

    # 7. Compute ranking per item_code (1 = lowest quoted_rate)
    from collections import defaultdict
    by_item = defaultdict(list)
    for r in responses:
        by_item[r["item_code"]].append(r)

    all_responses = []
    for item_code, rows in by_item.items():
        rows_sorted = sorted(rows, key=lambda x: x["quoted_rate"])
        for rank, row in enumerate(rows_sorted, start=1):
            row["ranking"] = rank
            all_responses.append(row)

    for resp in all_responses:
        comparison.append("vendor_responses", resp)

    # 8. Save
    comparison.insert(ignore_permissions=False)
    frappe.db.commit()

    return comparison.name


@frappe.whitelist()
def get_rate_history(item_code, months=24):
    """
    Return last `months` months of price history for an item
    from Supplier Quotations and Purchase Orders.

    Returns list of dicts ordered by date descending:
      [{"date", "vendor", "rate", "source", "reference"}, ...]
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
        """,
        {"cutoff": cutoff_date, "item_code": item_code},
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
        """,
        {"cutoff": cutoff_date, "item_code": item_code},
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
    """
    Approve a PEPL Quotation Comparison and auto-create
    draft Purchase Orders, one per selected_vendor.

    Returns list of created PO names.
    """
    # 1. Load doc
    comparison = frappe.get_doc("PEPL Quotation Comparison", comparison_name)

    # 2. Permission check
    user_roles = frappe.get_roles(frappe.session.user)
    if not any(r in user_roles for r in ("Purchase Manager", "System Manager")):
        frappe.throw(_("Only Purchase Manager can approve a Quotation Comparison."))

    # 3. Status check
    if comparison.status in ("Approved", "Cancelled"):
        frappe.throw(
            _("Comparison {0} is already {1} and cannot be approved again.").format(
                comparison_name, comparison.status
            )
        )

    # 4. Validate every item has selected_vendor + selected_rate
    incomplete = [
        row.item_code or f"Row {row.idx}"
        for row in (comparison.comparison_items or [])
        if not row.selected_vendor or not row.selected_rate
    ]
    if incomplete:
        frappe.throw(
            _("Selected Vendor and Rate are required for: {0}").format(", ".join(incomplete))
        )

    # 5. Validate override reasons
    override_missing = [
        row.item_code or f"Row {row.idx}"
        for row in (comparison.comparison_items or [])
        if flt(row.original_quoted_rate)
        and abs(flt(row.selected_rate) - flt(row.original_quoted_rate)) > 0.01
        and not row.override_reason
    ]
    if override_missing:
        frappe.throw(
            _("Override Reason is required for items with rate changes: {0}").format(
                ", ".join(override_missing)
            )
        )

    # 6. Group items by selected_vendor
    from collections import defaultdict
    vendor_items = defaultdict(list)
    for row in (comparison.comparison_items or []):
        vendor_items[row.selected_vendor].append(row)

    # 7. Create one draft PO per vendor
    today = nowdate()
    po_names = []
    override_entries = json.loads(comparison.override_log or "[]")

    for vendor, items in vendor_items.items():
        # Determine schedule_date = max(required_by) or today+30
        required_dates = [
            str(row.required_by)
            for row in items
            if row.required_by
        ]
        if required_dates:
            schedule_date = max(required_dates)
        else:
            schedule_date = add_months(today, 1)

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

        po.insert(ignore_permissions=False)
        po_names.append(po.name)

        # 8. Build override log entries
        for row in items:
            orig = flt(row.original_quoted_rate)
            sel = flt(row.selected_rate)
            if orig and abs(sel - orig) > 0.01:
                override_entries.append({
                    "item_code": row.item_code,
                    "vendor": vendor,
                    "old_rate": orig,
                    "new_rate": sel,
                    "reason": row.override_reason or "",
                    "user": frappe.session.user,
                    "ts": str(now_datetime()),
                })

    # 9. Update comparison doc
    comparison.status = "Approved"
    comparison.approved_by = frappe.session.user
    comparison.approved_on = now_datetime()
    comparison.generated_pos = ",".join(po_names)
    comparison.override_log = json.dumps(override_entries, default=str)

    # 10. Save
    comparison.save(ignore_permissions=False)

    # 11. Commit
    frappe.db.commit()

    return po_names
