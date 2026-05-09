# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import html as html_module

import frappe
from frappe import _
from frappe.utils import flt

from pepl_os.pepl_os.api.cst_intelligence import get_qualified_vendors_for_item

STANDARD_USERS = ("Guest", "Administrator")


def _source_public_label(source_key: str) -> str:
    m = {
        "approved_specific_item": "Item History",
        "approved_rm_group": "RM Group Match",
        "po_history": "PO History",
        "Manual Override": "Manual Override",
    }
    return m.get(source_key, source_key or "")


def _ensure_rfq_read(rfq_name: str):
    if not frappe.has_permission("Request for Quotation", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    frappe.get_doc("Request for Quotation", rfq_name)


def _ensure_rfq_write(rfq_name: str):
    if not frappe.has_permission("Request for Quotation", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)


def _rfq_phase2_installed() -> bool:
    return frappe.get_meta("Request for Quotation").has_field(
        "per_item_vendor_selections",
    )


@frappe.whitelist()
def populate_per_item_vendors(rfq_name):
    """Rebuild qualified rows in per_item_vendor_selections.

    Deletes is_qualified=1 rows (auto-managed by this function).
    Keeps is_qualified=0 rows (manual overrides, user-controlled).
    Re-inserts qualified vendors from 3-tier logic for every items row.
    Returns {"populated": N, "preserved": M}.
    """
    if not rfq_name:
        frappe.throw(_("RFQ name required"))
    _ensure_rfq_write(rfq_name)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    if not _rfq_phase2_installed():
        frappe.throw(_("PEPL Phase 2 custom field missing. Run migrations."))

    kept = [
        r for r in (rfq.get("per_item_vendor_selections") or [])
        if int(getattr(r, "is_qualified", 1) or 1) == 0
    ]
    preserved = len(kept)
    rfq.set("per_item_vendor_selections", kept)

    populated = 0
    for it in rfq.items or []:
        if not it.item_code:
            continue
        res = get_qualified_vendors_for_item(it.item_code, lookback_months=18) or {}
        for srow in res.get("suppliers") or []:
            sup = srow.get("supplier")
            if not sup:
                continue
            rfq.append(
                "per_item_vendor_selections",
                {
                    "rfq_item_idx": it.idx,
                    "rfq_item_code": it.item_code,
                    "vendor": sup,
                    "is_qualified": 1,
                    "source": _source_public_label(srow.get("source")),
                    "is_selected": 1,
                },
            )
            populated += 1

    rfq.save(ignore_permissions=True)
    frappe.db.commit()
    return {"populated": populated, "preserved": preserved}


@frappe.whitelist()
def get_per_item_qualified_vendors(rfq_name):
    """Return locked response shape:
    {items: [{rfq_item_idx, item_code, item_name, qty, uom,
              qualified_vendors: [{vendor, vendor_name, source, is_qualified}]}]}
    Reads from per_item_vendor_selections (populated by populate_per_item_vendors).
    """
    if not rfq_name:
        frappe.throw(_("RFQ name required"))
    _ensure_rfq_read(rfq_name)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    out = []

    for it in rfq.items or []:
        if not it.item_code:
            continue

        qualified_vendors = []
        for r in rfq.get("per_item_vendor_selections") or []:
            if (
                int(r.rfq_item_idx or 0) == int(it.idx)
                and r.rfq_item_code == it.item_code
                and int(getattr(r, "is_qualified", 1) or 1) == 1
                and r.vendor
            ):
                qualified_vendors.append(
                    {
                        "vendor": r.vendor,
                        "vendor_name": frappe.db.get_value(
                            "Supplier", r.vendor, "supplier_name"
                        ) or r.vendor,
                        "source": r.source or "",
                        "is_qualified": 1,
                    }
                )

        nm = frappe.db.get_value("Item", it.item_code, "item_name") or ""

        out.append(
            {
                "rfq_item_idx": it.idx,
                "item_code": it.item_code,
                "item_name": nm or it.item_name or it.item_code,
                "qty": flt(it.qty),
                "uom": it.uom or frappe.db.get_value(
                    "Item", it.item_code, "stock_uom"
                ) or "",
                "qualified_vendors": qualified_vendors,
            },
        )

    return {"items": out}


def _aggregate_vendor_item_rows(rfq_name: str):
    """Validate coverage and return {vendor: [email row dicts]}."""
    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    if not _rfq_phase2_installed():
        frappe.throw(_("PEPL Phase 2 custom field missing. Run migrations."))

    selections = list(rfq.get("per_item_vendor_selections") or [])
    active = [
        r
        for r in selections
        if r.is_selected
        and r.vendor
        and r.rfq_item_code
        and r.rfq_item_idx not in (None, 0)
    ]

    item_rows_with_code = [it for it in (rfq.items or []) if it.item_code]
    if not item_rows_with_code:
        frappe.throw(_("No items with Item Code on this RFQ"))

    missing = []
    for it in item_rows_with_code:
        count = sum(1 for r in active if int(r.rfq_item_idx) == int(it.idx))
        if count == 0:
            missing.append(it.item_code)

    if missing:
        frappe.throw(
            _(
                "Each RFQ item must have at least one selected vendor "
                "(PEPL Phase 2). Missing vendors for items: {0}"
            ).format(", ".join(missing)),
        )

    grouped = {}
    seen_pair = set()

    for r in active:
        key_pair = (r.vendor, str(r.rfq_item_code))
        if key_pair in seen_pair:
            continue
        seen_pair.add(key_pair)

        line = None
        for it in rfq.items or []:
            if int(it.idx) == int(r.rfq_item_idx) and it.item_code == r.rfq_item_code:
                line = it
                break

        qty = flt(line.qty) if line else None
        uom = ""
        if line:
            uom = (
                line.uom
                or frappe.db.get_value("Item", line.item_code, "stock_uom")
                or ""
            )

        grouped.setdefault(r.vendor, []).append(
            {
                "rfq_item_idx": int(r.rfq_item_idx),
                "item_code": r.rfq_item_code,
                "item_name": frappe.db.get_value(
                    "Item", r.rfq_item_code, "item_name"
                ) or r.rfq_item_code,
                "qty": qty,
                "uom": uom,
                "is_manual_override": int(getattr(r, "is_qualified", 1) or 0) == 0
                or (r.source or "") == "Manual Override",
                "source_label": r.source or "",
                "notes": r.notes or "",
            },
        )

    return grouped


@frappe.whitelist()
def aggregate_selections_by_vendor(rfq_name):
    """Whitelisted: {supplier: [item_codes]} for dashboards / previews."""
    if not rfq_name:
        frappe.throw(_("RFQ name required"))
    _ensure_rfq_read(rfq_name)
    agr = _aggregate_vendor_item_rows(rfq_name)
    return {sup: [row["item_code"] for row in rows] for sup, rows in agr.items()}


def _items_email_table(rows: list) -> str:
    if not rows:
        return ""

    h_code = html_module.escape(_("Item Code"))
    h_name = html_module.escape(_("Item Name"))
    h_qty = html_module.escape(_("Qty"))
    h_uom = html_module.escape(_("UOM"))

    tbl = [
        '<table cellpadding="8" cellspacing="0" border="1" '
        'style="border-collapse:collapse;font-size:13px;width:100%;">',
        f"<thead><tr><th>M</th><th>{h_code}</th><th>{h_name}</th>"
        f"<th>{h_qty}</th><th>{h_uom}</th></tr></thead><tbody>",
    ]

    for row in sorted(rows, key=lambda x: x.get("item_code") or ""):
        mcell = "M" if row.get("is_manual_override") else ""
        qty = row.get("qty")
        qty_s = "" if qty in (None, "") else str(flt(qty)).rstrip("0").rstrip(".")

        tbl.append("<tr>")
        tbl.append(f"<td>{html_module.escape(str(mcell))}</td>")
        tbl.append(f"<td>{html_module.escape(str(row.get('item_code') or ''))}</td>")
        tbl.append(f"<td>{html_module.escape(str(row.get('item_name') or ''))}</td>")
        tbl.append(f"<td>{html_module.escape(str(qty_s))}</td>")
        tbl.append(f"<td>{html_module.escape(str(row.get('uom') or ''))}</td>")
        tbl.append("</tr>")

    tbl.append("</tbody></table>")
    lbl = html_module.escape(_("M marks manual override vendor/item pairings."))
    tbl.append(f"<p><small>{lbl}</small></p>")
    return "".join(tbl)


def _sender():
    fixed_procurement_email = frappe.db.get_single_value("Buying Settings", "fixed_email")
    if fixed_procurement_email:
        return frappe.db.get_value("Email Account", fixed_procurement_email, "email_id")
    uid = frappe.session.user
    if uid not in STANDARD_USERS:
        return uid
    return None


@frappe.whitelist()
def send_rfq_emails_phase2(rfq_name):
    if not rfq_name:
        frappe.throw(_("RFQ name required"))

    _ensure_rfq_write(rfq_name)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)

    if rfq.docstatus != 1:
        frappe.throw(_("Submit the RFQ before sending supplier emails"))

    if not (rfq.get("per_item_vendor_selections") or []):
        frappe.throw(
            _("No Phase 2 vendor selections found. Use 'Configure Vendors per Item' first.")
        )

    grouped = _aggregate_vendor_item_rows(rfq_name)

    if not grouped:
        frappe.throw(_("Aggregation returned no vendors to email."))

    sender = _sender()
    sent_count = 0
    skipped = []
    summaries = []

    for vendor_name, rows in grouped.items():
        email = frappe.db.get_value("Supplier", vendor_name, "email_id")
        if not email:
            skipped.append(vendor_name)
            frappe.log_error(
                f"RFQ Phase 2: no email_id on Supplier {vendor_name!r} — skipped",
                f"RFQ {rfq_name} email skip",
            )
            summaries.append(
                _("Skipped {0}: no email on Supplier record").format(vendor_name)
            )
            continue

        supplier_display = (
            frappe.db.get_value("Supplier", vendor_name, "supplier_name") or vendor_name
        )
        subject = _("RFQ {0} from PEPL \u2014 Quote requested").format(rfq_name)

        body_chunks = []
        body_chunks.append(
            "<p>" + html_module.escape(_("Dear {0},").format(supplier_display)) + "</p>"
        )
        body_chunks.append(
            "<p>" + html_module.escape(
                _("Please quote for the following items from RFQ {0}:").format(rfq_name)
            ) + "</p>"
        )
        body_chunks.append(_items_email_table(rows))
        body_chunks.append(
            "<p>" + html_module.escape(
                _("Please reply with your best quotation including unit rate, lead time, and validity.")
            ) + "</p>"
        )
        body_chunks.append(
            "<p>" + html_module.escape(
                _("Regards, Parasramka Engineering Pvt. Ltd.")
            ) + "</p>"
        )
        html_body = "".join(body_chunks)

        try:
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=html_body,
                sender=sender,
                reference_doctype="Request for Quotation",
                reference_name=rfq_name,
                delayed=False,
            )
            sent_count += 1
            summaries.append(
                _("Email sent to {0} ({1})").format(supplier_display, email)
            )
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(), f"RFQ Phase 2 send: {vendor_name}"
            )
            summaries.append(
                _("Failed to email {0}: {1}").format(vendor_name, str(e))
            )

    frappe.db.commit()
    return {"sent": sent_count, "skipped": skipped, "summaries": summaries}
