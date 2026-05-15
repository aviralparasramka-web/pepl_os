# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# PEPL Receipt Log — server-side functions and doc_events hooks.

import frappe
from frappe import _
from frappe.utils import nowdate, flt


DOC_TYPE_MAPPING = {
    "mill test certificate": "Mill Test Certificate",
    "mill tc": "Mill Test Certificate",
    "mtc": "Mill Test Certificate",
    "heat treatment chart": "Heat Treatment Chart",
    "heat treatment": "Heat Treatment Chart",
    "ht chart": "Heat Treatment Chart",
    "vendor inspection report": "Vendor Inspection Report",
    "vir": "Vendor Inspection Report",
    "dealership": "Dealership/Authorization Certificate",
    "authorization certificate": "Dealership/Authorization Certificate",
    "internal qc": "Internal QC Report",
    "qc report": "Internal QC Report",
    "nabl": "NABL Lab Test Report",
    "lab test": "NABL Lab Test Report",
    "conformity": "Conformity Certificate",
    "coc": "Conformity Certificate",
}


def _match_doc_type(text):
    """Match free-text to the doc_type Select options. Falls back to Other."""
    if not text:
        return "Other"
    text_lower = text.lower().strip()
    for keyword, doc_type in DOC_TYPE_MAPPING.items():
        if keyword in text_lower:
            return doc_type
    return "Other"


def auto_create_on_pr_submit(doc, method):
    """Purchase Receipt on_submit: create one Receipt Log per stock item.
    Pre-populates document checklist from PO's expected_documents.
    Creates or appends to Heat Number Trace if heat_number is present."""
    try:
        # Get expected docs from PO (first PO found on items)
        po_name = None
        for item in (doc.items or []):
            po = getattr(item, "purchase_order", None)
            if po:
                po_name = po
                break

        expected_docs_text = ""
        if po_name:
            expected_docs_text = frappe.db.get_value(
                "Purchase Order", po_name, "expected_documents"
            ) or ""

        expected_doc_list = [
            s.strip() for s in expected_docs_text.split(",") if s.strip()
        ] if expected_docs_text else []

        for item in (doc.items or []):
            is_stock = frappe.db.get_value("Item", item.item_code, "is_stock_item")
            if not is_stock:
                continue

            # Idempotency
            existing = frappe.db.get_value(
                "PEPL Receipt Log",
                {
                    "linked_purchase_receipt": doc.name,
                    "item_code": item.item_code,
                },
                "name",
            )
            if existing:
                continue

            # Heat number can be on item or parent
            heat_number = (
                getattr(item, "heat_number", None)
                or getattr(doc, "heat_number", None)
                or ""
            )

            log = frappe.new_doc("PEPL Receipt Log")
            log.linked_purchase_receipt = doc.name
            log.linked_po = po_name
            log.supplier = doc.supplier
            log.posting_date = doc.posting_date
            log.item_code = item.item_code
            log.item_name = item.item_name
            log.qty_received = flt(item.qty)
            log.uom = item.uom
            log.heat_number = heat_number
            log.warehouse = item.warehouse

            insp_req = frappe.db.get_value(
                "Item", item.item_code, "inspection_required_before_purchase"
            )
            log.inspection_required = 1 if insp_req else 0
            log.qc_status = "Pending" if insp_req else "Not Required"

            for doc_text in expected_doc_list:
                matched = _match_doc_type(doc_text)
                log.append("documents", {
                    "doc_type": matched,
                    "doc_type_other": doc_text if matched == "Other" else None,
                    "required": 1,
                    "received": 0,
                })

            log.insert(ignore_permissions=True)

            if heat_number:
                _ensure_heat_trace(heat_number, item, doc, log, po_name)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"auto_create_on_pr_submit failed for PR {doc.name}: {e}",
            "Receipt Log Hook",
        )


def _ensure_heat_trace(heat_number, item, pr_doc, log, po_name):
    """Create or append to PEPL Heat Number Trace."""
    existing = frappe.db.exists("PEPL Heat Number Trace", heat_number)

    if existing:
        trace = frappe.get_doc("PEPL Heat Number Trace", existing)
    else:
        trace = frappe.new_doc("PEPL Heat Number Trace")
        trace.heat_number = heat_number
        trace.item_code = item.item_code
        trace.item_name = item.item_name
        trace.source_supplier = pr_doc.supplier
        trace.source_po = po_name
        trace.source_grn = pr_doc.name

    already_logged = any(
        u.event_type == "Received" and u.reference_name == pr_doc.name
        for u in (trace.usage_log or [])
    )
    if not already_logged:
        trace.append("usage_log", {
            "event_date": pr_doc.posting_date or nowdate(),
            "event_type": "Received",
            "reference_doctype": "Purchase Receipt",
            "reference_name": pr_doc.name,
            "qty": flt(item.qty),
            "user": frappe.session.user,
        })

    if existing:
        trace.save(ignore_permissions=True)
    else:
        trace.insert(ignore_permissions=True)


def update_qc_on_qi_submit(doc, method):
    """Quality Inspection on_submit: update linked Receipt Log's qc_status."""
    try:
        if getattr(doc, "reference_type", None) != "Purchase Receipt":
            return

        pr_name = doc.reference_name
        item_code = doc.item_code

        log_name = frappe.db.get_value(
            "PEPL Receipt Log",
            {
                "linked_purchase_receipt": pr_name,
                "item_code": item_code,
            },
            "name",
        )
        if not log_name:
            return

        new_status = "Passed" if doc.status == "Accepted" else "Failed"
        frappe.db.set_value("PEPL Receipt Log", log_name, {
            "qc_status": new_status,
            "linked_quality_inspection": doc.name,
        })
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"update_qc_on_qi_submit failed for QI {doc.name}: {e}",
            "Receipt Log Hook",
        )


@frappe.whitelist()
def add_document(log_name, doc_type, doc_type_other=None, required=1, remarks=None):
    """QA amends a Receipt Log by adding a new required document."""
    log = frappe.get_doc("PEPL Receipt Log", log_name)
    log.append("documents", {
        "doc_type": doc_type,
        "doc_type_other": doc_type_other,
        "required": int(required),
        "received": 0,
        "remarks": remarks or "",
    })
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "added"}
