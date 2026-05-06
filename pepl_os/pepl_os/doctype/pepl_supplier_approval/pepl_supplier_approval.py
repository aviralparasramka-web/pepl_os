# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


MANDATORY_DOCS = [
    "NDA",
    "Tie-up Letter",
    "List of Plant and Machinery",
    "List of Instruments",
    "List of Approvals",
    "ISO Certificate",
    "Product List",
    "GST Certificate",
    "PAN",
    "Bank Details",
    "TAN Number",
]

OPTIONAL_DOCS = [
    "AS9100 Certificate",
    "IATF 16949 Certificate",
    "Audited Financials",
    "Factory License",
    "Pollution Certificate",
]


class PEPLSupplierApproval(Document):
    """Master DocType for tracking supplier approval status, document
    checklist, and suspension state. One record per Supplier.

    Auto-status logic, expiry computation, pending-docs auto-list,
    and document status auto-advance are added in Day 4.
    """

    def before_insert(self):
        """Pre-populate the Mandatory and Optional document checklists
        on first creation so the user only fills in attachments + dates.
        """
        if not self.mandatory_documents:
            for doc_name in MANDATORY_DOCS:
                self.append("mandatory_documents", {"doc_type": doc_name})

        if not self.optional_documents:
            for doc_name in OPTIONAL_DOCS:
                self.append("optional_documents", {"doc_type": doc_name})
