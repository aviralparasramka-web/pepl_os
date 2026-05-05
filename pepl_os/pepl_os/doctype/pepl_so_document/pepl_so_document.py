import frappe
from frappe import _
from frappe.model.document import Document


class PEPLSODocument(Document):
    def validate(self):
        if self.source == "Auto-Copied from Tender" and self.attachments:
            self._check_version_drift()

    def _check_version_drift(self):
        """Compare current attachments against source files (simple filename check).
        Manual flag is the primary mechanism; auto-detection reserved for future."""
        pass


@frappe.whitelist()
def create_so_documents_for_sales_order(sales_order_name, source_tender=None):
    """Auto-populate SO Documents when SO is submitted.
    Called from SO on_submit hook OR when Tender creates SO.

    Auto-creates placeholder records for: Customer PO, and NDA (from Tender if available).
    """
    so = frappe.get_doc("Sales Order", sales_order_name)
    created = []

    # 1. Customer PO record
    if not frappe.db.exists("PEPL SO Document", {
        "linked_sales_order": sales_order_name,
        "document_type": "Customer PO"
    }):
        po_doc = frappe.new_doc("PEPL SO Document")
        po_doc.linked_sales_order = sales_order_name
        po_doc.customer = so.customer
        po_doc.document_type = "Customer PO"
        po_doc.document_title = f"Customer PO {so.po_no}" if so.po_no else "Customer PO"
        po_doc.reference_number = so.po_no or ""
        po_doc.document_date = so.po_date or so.transaction_date
        po_doc.document_status = "Received"
        po_doc.direction = "Inbound (from Customer)"
        po_doc.source = "Auto-Generated"
        po_doc.insert(ignore_permissions=True)
        created.append(po_doc.name)

    # 2. If source tender provided, copy NDA from bid documents
    if source_tender:
        try:
            tender = frappe.get_doc("PEPL Tender", source_tender)

            for bid_doc in (tender.bid_documents or []):
                if bid_doc.document_type and "NDA" in bid_doc.document_type.upper():
                    if not frappe.db.exists("PEPL SO Document", {
                        "linked_sales_order": sales_order_name,
                        "document_type": "NDA"
                    }):
                        nda_doc = frappe.new_doc("PEPL SO Document")
                        nda_doc.linked_sales_order = sales_order_name
                        nda_doc.customer = so.customer
                        nda_doc.document_type = "NDA"
                        nda_doc.document_title = "NDA (carried from Tender)"
                        nda_doc.document_date = tender.bid_submission_deadline or so.transaction_date
                        nda_doc.document_status = "Filed"
                        nda_doc.direction = "Outbound (to Customer)"
                        nda_doc.source = "Auto-Copied from Tender"
                        nda_doc.source_reference = source_tender
                        nda_doc.insert(ignore_permissions=True)
                        created.append(nda_doc.name)
                    break  # Only one NDA per SO

        except Exception as e:
            frappe.log_error(
                f"Failed to copy tender docs to SO {sales_order_name}: {str(e)}",
                "Module 5 SO Doc Auto-Copy"
            )

    return {"created": created, "count": len(created)}
