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
            # Read expected_documents from either fieldname (auto-prefixed
            # variant takes precedence if both exist)
            expected_docs_text = (
                frappe.db.get_value(
                    "Purchase Order", po_name, "custom_expected_documents_at_receipt"
                )
                or frappe.db.get_value(
                    "Purchase Order", po_name, "expected_documents"
                )
                or ""
            )

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

            # Heat number can be on item or parent, with optional custom_ prefix
            heat_number = (
                getattr(item, "heat_number", None)
                or getattr(item, "custom_heat_number", None)
                or getattr(doc, "heat_number", None)
                or getattr(doc, "custom_heat_number", None)
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

            # Pre-populate one heat_details row if a heat_number was on the PR.
            # Stores splits this into multiple rows after auto-creation.
            if heat_number:
                log.append("heat_details", {
                    "heat_number": heat_number,
                    "qty": flt(item.qty),
                    "heat_trace_status": 0,
                })

            log.insert(ignore_permissions=True)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"auto_create_on_pr_submit failed for PR {doc.name}: {e}",
            "Receipt Log Hook",
        )


def ensure_heat_trace_from_log_row(log, row):
    """Create/append Heat Trace from a Receipt Log heat_details row.
    Called from PEPLReceiptLog.on_submit and on_update_after_submit.
    Returns True if Trace was created or updated."""
    try:
        heat_number = row.heat_number
        if not heat_number:
            return False

        existing = frappe.db.exists("PEPL Heat Number Trace", heat_number)
        if existing:
            trace = frappe.get_doc("PEPL Heat Number Trace", existing)
        else:
            trace = frappe.new_doc("PEPL Heat Number Trace")
            trace.heat_number = heat_number
            trace.item_code = log.item_code
            trace.item_name = log.item_name
            trace.source_supplier = log.supplier
            trace.source_po = log.linked_po
            trace.source_grn = log.linked_purchase_receipt
            if row.material_grade:
                trace.material_grade = row.material_grade

        # Idempotency: skip if this exact (PR, qty, heat) combo already logged
        already_logged = any(
            u.event_type == "Received"
            and u.reference_name == log.linked_purchase_receipt
            and abs(flt(u.qty) - flt(row.qty)) < 0.001
            for u in (trace.usage_log or [])
        )
        if not already_logged:
            trace.append("usage_log", {
                "event_date": log.posting_date or nowdate(),
                "event_type": "Received",
                "reference_doctype": "Purchase Receipt",
                "reference_name": log.linked_purchase_receipt,
                "qty": flt(row.qty),
                "user": frappe.session.user,
            })

        if existing:
            trace.save(ignore_permissions=True)
        else:
            trace.insert(ignore_permissions=True)

        frappe.db.commit()
        return True
    except Exception as e:
        frappe.log_error(
            f"ensure_heat_trace_from_log_row failed for {row.heat_number}: {e}",
            "Receipt Log Hook",
        )
        return False


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
