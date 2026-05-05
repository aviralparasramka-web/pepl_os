import frappe
from frappe import _


def on_submit(doc, method=None):
    """Triggered when Sales Order is submitted.
    Module 5 actions (refactored):
    1. Auto-create one PSD Tracker per SO (with one default PSD Entry)
    2. Auto-create one Document Tracker per SO (with default Customer PO entry,
       plus NDA from Tender if applicable)
    """
    try:
        # 1. Create PSD Tracker
        from pepl_os.pepl_os.doctype.pepl_psd_tracker.pepl_psd_tracker import create_psd_tracker_for_so
        psd_result = create_psd_tracker_for_so(doc.name)

        if psd_result.get("created"):
            frappe.msgprint(
                _("PSD Tracker {0} created (Sector: {1}, Initial PSD: {2}%)").format(
                    psd_result.get("tracker_name"),
                    psd_result.get("sector"),
                    psd_result.get("percentage")
                ),
                indicator="green",
                alert=True
            )

        # 2. Detect source tender for NDA copy
        source_tender = None
        if hasattr(doc, "custom_tender_reference") and doc.custom_tender_reference:
            source_tender = doc.custom_tender_reference

        # 3. Create Document Tracker
        from pepl_os.pepl_os.doctype.pepl_document_tracker.pepl_document_tracker import create_doc_tracker_for_so
        doc_result = create_doc_tracker_for_so(doc.name, source_tender)

        if doc_result.get("created"):
            frappe.msgprint(
                _("Document Tracker {0} created with {1} initial entries").format(
                    doc_result.get("tracker_name"),
                    doc_result.get("entries_count")
                ),
                indicator="blue",
                alert=True
            )

    except Exception as e:
        frappe.log_error(
            f"Module 5 auto-creation failed for SO {doc.name}: {str(e)}",
            "Module 5 SO On Submit"
        )
