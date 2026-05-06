# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, today


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

EXPIRING_SOON_DAYS = 30
SUSPENSION_STATES = ["Temporary Suspended", "Permanent Suspended"]


class PEPLSupplierApproval(Document):
    """Master DocType for supplier approval. One record per Supplier."""

    def before_insert(self):
        """Pre-populate Mandatory and Optional checklists."""
        if not self.mandatory_documents:
            for doc_name in MANDATORY_DOCS:
                self.append("mandatory_documents", {"doc_type": doc_name})
        if not self.optional_documents:
            for doc_name in OPTIONAL_DOCS:
                self.append("optional_documents", {"doc_type": doc_name})

    def validate(self):
        """Recalculate row statuses, build pending list, auto-advance
        if expired, and validate the approval_status against rules."""
        self._update_document_row_statuses()
        self._compute_pending_docs_list()
        self._auto_advance_to_expired()
        self._validate_status_transitions()

    def on_update(self):
        """After save, sync approval_status back to the linked Supplier
        so it's queryable on Supplier list view and in RFQ filters."""
        if self.linked_supplier:
            frappe.db.set_value(
                "Supplier",
                self.linked_supplier,
                "pepl_approval_status",
                self.approval_status,
                update_modified=False,
            )

    # ─────────────────────────────────────────────
    # Row-level status calculation
    # ─────────────────────────────────────────────

    def _update_document_row_statuses(self):
        for table_field in ["mandatory_documents", "optional_documents", "other_documents"]:
            for row in (self.get(table_field) or []):
                self._update_single_row_status(row)

    def _update_single_row_status(self, row):
        if not row.attach:
            row.status = "Not Submitted"
            row.days_to_expiry = 0
            return
        if not row.expiry_date:
            row.status = "Submitted"
            row.days_to_expiry = 0
            return
        days = date_diff(row.expiry_date, today())
        row.days_to_expiry = days
        if days < 0:
            row.status = "Expired"
        elif days <= EXPIRING_SOON_DAYS:
            row.status = "Expiring Soon"
        else:
            row.status = "Submitted"

    def _compute_pending_docs_list(self):
        pending = [
            r.doc_type or "Unknown"
            for r in (self.mandatory_documents or [])
            if not r.attach
        ]
        if pending:
            self.pending_docs_list = ", ".join(pending)
        else:
            self.pending_docs_list = "All 11 mandatory documents attached."

    def _auto_advance_to_expired(self):
        if self.approval_status not in ["Approved", "Approved (Documents Pending)"]:
            return
        expired_rows = [r for r in (self.mandatory_documents or []) if r.status == "Expired"]
        if not expired_rows:
            return
        expired_names = [r.doc_type for r in expired_rows]
        self.approval_status = "Expired"
        msg = "Auto-moved to Expired on {0}: {1}".format(today(), ", ".join(expired_names))
        self.remarks = (self.remarks + "\n\n" + msg) if self.remarks else msg

    def _validate_status_transitions(self):
        if self.approval_status == "Approved":
            missing = [r.doc_type for r in (self.mandatory_documents or []) if not r.attach]
            if missing:
                frappe.throw(_(
                    "Cannot set status to Approved. Missing mandatory documents: {0}. "
                    "Either attach these documents, or use 'Approved (Documents Pending)' "
                    "with the override flag and reason."
                ).format(", ".join(missing)))
            expired = [r.doc_type for r in (self.mandatory_documents or []) if r.status == "Expired"]
            if expired:
                frappe.throw(_(
                    "Cannot set status to Approved. Expired mandatory documents: {0}. "
                    "Update these documents first."
                ).format(", ".join(expired)))
            if not self.approval_date:
                self.approval_date = today()
            if not self.approved_by:
                self.approved_by = frappe.session.user

        elif self.approval_status == "Approved (Documents Pending)":
            if not self.approved_with_pending_docs:
                frappe.throw(_(
                    "To set status as 'Approved (Documents Pending)', tick "
                    "'Approved with Pending Documents' and provide a reason."
                ))
            if not self.pending_docs_reason:
                frappe.throw(_(
                    "Pending Docs Reason is required when status is "
                    "'Approved (Documents Pending)'."
                ))
            if not self.approval_date:
                self.approval_date = today()
            if not self.approved_by:
                self.approved_by = frappe.session.user

        elif self.approval_status in SUSPENSION_STATES:
            if not self.suspension_reason:
                frappe.throw(_(
                    "Suspension Reason is required when status is {0}."
                ).format(self.approval_status))
            if not self.suspension_date:
                self.suspension_date = today()


def update_all_supplier_approvals_daily():
    """Scheduled daily — re-save every record to recalculate document
    statuses and trigger auto-advance based on current date."""
    suppliers = frappe.get_all("PEPL Supplier Approval", pluck="name")
    failed = []
    for name in suppliers:
        try:
            doc = frappe.get_doc("PEPL Supplier Approval", name)
            doc.save(ignore_permissions=True)
        except Exception as e:
            failed.append(name)
            frappe.log_error(
                f"Failed to update Supplier Approval {name}: {str(e)}",
                "Supplier Approval Daily Update"
            )
    if failed:
        frappe.log_error(
            f"Daily update failed for {len(failed)} records: {', '.join(failed)}",
            "Supplier Approval Daily Update Summary"
        )
