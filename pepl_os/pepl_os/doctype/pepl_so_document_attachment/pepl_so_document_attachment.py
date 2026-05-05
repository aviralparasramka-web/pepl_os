import frappe
from frappe.model.document import Document


class PEPLSODocumentAttachment(Document):
    def validate(self):
        if not self.uploaded_by:
            self.uploaded_by = frappe.session.user
