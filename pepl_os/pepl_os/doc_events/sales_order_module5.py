import frappe
from frappe import _


def on_submit(doc, method=None):
    """Triggered when Sales Order is submitted.
    Module 5 actions:
    1. Auto-create PSD Tracker (Defence 5%, others 0%)
    2. Auto-populate SO Document Library (Customer PO + NDA from Tender if available)
    """
    try:
        # 1. Create PSD Tracker
        from pepl_os.pepl_os.doctype.pepl_psd_tracker.pepl_psd_tracker import (
            create_psd_for_sales_order,
        )
        psd_result = create_psd_for_sales_order(doc.name)

        if psd_result.get("created"):
            frappe.msgprint(
                _("PSD Tracker {0} created automatically (Sector: {1}, %: {2})").format(
                    psd_result.get("psd_name"),
                    psd_result.get("sector"),
                    psd_result.get("percentage"),
                ),
                indicator="green",
                alert=True,
            )

        # 2. Auto-populate SO Document Library
        source_tender = None
        if hasattr(doc, "custom_tender_reference") and doc.custom_tender_reference:
            source_tender = doc.custom_tender_reference

        from pepl_os.pepl_os.doctype.pepl_so_document.pepl_so_document import (
            create_so_documents_for_sales_order,
        )
        doc_result = create_so_documents_for_sales_order(doc.name, source_tender)

        if doc_result.get("count", 0) > 0:
            frappe.msgprint(
                _("Auto-populated {0} SO Document record(s)").format(doc_result.get("count")),
                indicator="blue",
                alert=True,
            )

    except Exception as e:
        # Log but do NOT block SO submit
        frappe.log_error(
            f"Module 5 auto-creation failed for SO {doc.name}: {str(e)}",
            "Module 5 SO On Submit",
        )
