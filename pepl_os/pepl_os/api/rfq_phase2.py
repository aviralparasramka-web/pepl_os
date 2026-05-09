# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import html as html_module

import frappe
from frappe import _
from frappe.utils import flt

from pepl_os.pepl_os.api.cst_intelligence import get_qualified_vendors_for_item

STANDARD_USERS = ("Guest", "Administrator")

_SOURCE_TIER = {
    "approved_specific_item": 1,
    "approved_rm_group": 2,
    "po_history": 3,
}

_SOURCE_LABEL = {
    "approved_specific_item": "Approved — Item History",
    "approved_rm_group": "Approved — RM Group",
    "po_history": "PO History",
}


def _ensure_rfq_read(rfq_name: str):
    if not frappe.has_permission("Request for Quotation", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    frappe.get_doc("Request for Quotation", rfq_name)


def _ensure_rfq_write(rfq_name: str):
    if not frappe.has_permission("Request for Quotation", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)


def _target_vendors_installed() -> bool:
    return frappe.get_meta("Request for Quotation Item").has_field("target_vendors")


@frappe.whitelist()
def get_qualified_vendors_per_item(rfq_name):
    """Return 3-tier qualified vendors for every RFQ Item row.

    Response shape (locked):
    {
        items: [{
            rfq_item_idx,        # int — matches frm.doc.items[n].idx
            item_code,
            item_name,
            qty,
            uom,
            tier1: [{supplier, supplier_name, source_label}],   # Approved specific item
            tier2: [{supplier, supplier_name, source_label}],   # Approved RM group
            tier3: [{supplier, supplier_name, source_label}],   # PO history (no approval)
            current_vendors: [supplier, ...]                    # from item.target_vendors
        }]
    }
    """
    if not rfq_name:
        frappe.throw(_("RFQ name required"))
    _ensure_rfq_read(rfq_name)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)
    out = []

    for it in rfq.items or []:
        if not it.item_code:
            continue

        res = get_qualified_vendors_for_item(it.item_code, lookback_months=18) or {}
        tier1, tier2, tier3 = [], [], []
        for srow in res.get("suppliers") or []:
            sup = srow.get("supplier")
            if not sup:
                continue
            tier = _SOURCE_TIER.get(srow.get("source"), 3)
            entry = {
                "supplier": sup,
                "supplier_name": srow.get("supplier_name") or sup,
                "source_label": _SOURCE_LABEL.get(srow.get("source"), srow.get("source") or ""),
            }
            if tier == 1:
                tier1.append(entry)
            elif tier == 2:
                tier2.append(entry)
            else:
                tier3.append(entry)

        current_vendors = [
            tv.supplier
            for tv in (it.get("target_vendors") or [])
            if tv.supplier
        ]

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
                "tier1": tier1,
                "tier2": tier2,
                "tier3": tier3,
                "current_vendors": current_vendors,
            }
        )

    return {"items": out}


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
        f"<thead><tr><th>{h_code}</th><th>{h_name}</th>"
        f"<th>{h_qty}</th><th>{h_uom}</th></tr></thead><tbody>",
    ]

    for row in sorted(rows, key=lambda x: x.get("item_code") or ""):
        qty = row.get("qty")
        qty_s = "" if qty in (None, "") else str(flt(qty)).rstrip("0").rstrip(".")
        tbl.append("<tr>")
        tbl.append(f"<td>{html_module.escape(str(row.get('item_code') or ''))}</td>")
        tbl.append(f"<td>{html_module.escape(str(row.get('item_name') or ''))}</td>")
        tbl.append(f"<td>{html_module.escape(str(qty_s))}</td>")
        tbl.append(f"<td>{html_module.escape(str(row.get('uom') or ''))}</td>")
        tbl.append("</tr>")

    tbl.append("</tbody></table>")
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
    """Send one per-item-filtered email per supplier in rfq.suppliers.

    rfq.suppliers is auto-populated from target_vendors by the override controller
    on save/validate. For each supplier, only RFQ items that have that supplier
    in their target_vendors are included in the email.
    """
    if not rfq_name:
        frappe.throw(_("RFQ name required"))

    _ensure_rfq_write(rfq_name)

    rfq = frappe.get_doc("Request for Quotation", rfq_name)

    if rfq.docstatus != 1:
        frappe.throw(_("Submit the RFQ before sending supplier emails"))

    if not (rfq.suppliers or []):
        frappe.throw(
            _(
                "No suppliers on this RFQ. "
                "Configure vendors per item first (the Suppliers table is "
                "auto-populated from target_vendors on save)."
            )
        )

    if not _target_vendors_installed():
        frappe.throw(_("PEPL Phase 2 custom field target_vendors is not installed. Run migrations."))

    sender = _sender()
    sent_count = 0
    skipped = []
    summaries = []

    for sup_row in rfq.suppliers or []:
        vendor_name = sup_row.supplier
        if not vendor_name:
            continue

        # Collect items where this supplier is in target_vendors
        rows = []
        for it in rfq.items or []:
            if not it.item_code:
                continue
            tv_suppliers = {tv.supplier for tv in (it.get("target_vendors") or []) if tv.supplier}
            if vendor_name not in tv_suppliers:
                continue
            rows.append(
                {
                    "item_code": it.item_code,
                    "item_name": frappe.db.get_value("Item", it.item_code, "item_name")
                    or it.item_name
                    or it.item_code,
                    "qty": flt(it.qty),
                    "uom": it.uom
                    or frappe.db.get_value("Item", it.item_code, "stock_uom")
                    or "",
                }
            )

        if not rows:
            summaries.append(
                _("Skipped {0}: no items matched target_vendors").format(vendor_name)
            )
            continue

        # Resolve email from Supplier.email_id (supplier row may also carry it)
        email = sup_row.email_id or frappe.db.get_value("Supplier", vendor_name, "email_id")
        if not email:
            skipped.append(vendor_name)
            frappe.log_error(
                f"RFQ Phase 2: no email_id for Supplier {vendor_name!r} — skipped",
                f"RFQ {rfq_name} send skip",
            )
            summaries.append(
                _("Skipped {0}: no email on Supplier record").format(vendor_name)
            )
            continue

        supplier_display = (
            frappe.db.get_value("Supplier", vendor_name, "supplier_name") or vendor_name
        )
        subject = _("RFQ {0} from PEPL \u2014 Quote requested").format(rfq_name)

        body_chunks = [
            "<p>" + html_module.escape(_("Dear {0},").format(supplier_display)) + "</p>",
            "<p>" + html_module.escape(
                _("Please quote for the following items from RFQ {0}:").format(rfq_name)
            ) + "</p>",
            _items_email_table(rows),
            "<p>" + html_module.escape(
                _(
                    "Please reply with your best quotation including "
                    "unit rate, lead time, and validity."
                )
            ) + "</p>",
            "<p>" + html_module.escape(
                _("Regards, Parasramka Engineering Pvt. Ltd.")
            ) + "</p>",
        ]
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
