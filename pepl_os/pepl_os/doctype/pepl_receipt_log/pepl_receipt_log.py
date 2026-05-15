# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# PEPL Receipt Log — parent controller

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, add_months


class PEPLReceiptLog(Document):
    def validate(self):
        self._update_doc_expiry_dates()
        self._compute_doc_status()

    def on_update_after_submit(self):
        self._sync_heat_traces()

    def on_submit(self):
        self._sync_heat_traces()

    def _update_doc_expiry_dates(self):
        for row in (self.documents or []):
            if row.received_date and row.validity_months:
                try:
                    row.expiry_date = add_months(
                        getdate(row.received_date), int(row.validity_months)
                    )
                except Exception:
                    pass

    def _compute_doc_status(self):
        if not self.documents:
            self.documents_status = "Not Started"
            self.pending_doc_count = 0
            return

        required_docs = [d for d in self.documents if d.required]
        if not required_docs:
            self.documents_status = "Complete"
            self.pending_doc_count = 0
            return

        received_required = [d for d in required_docs if d.received]
        pending = len(required_docs) - len(received_required)
        today = getdate(nowdate())
        expired = 0
        for d in self.documents:
            if d.received and d.expiry_date and getdate(d.expiry_date) < today:
                expired += 1

        self.pending_doc_count = pending
        if pending > 0:
            self.documents_status = "Pending Items"
        elif expired > 0:
            self.documents_status = "Expired"
        else:
            self.documents_status = "Complete"

    def _sync_heat_traces(self):
        """Iterate heat_details and ensure a Heat Number Trace exists
        for each, with a Received event for this receipt."""
        from pepl_os.pepl_os.api.receipt_log import (
            ensure_heat_trace_from_log_row,
        )
        for row in (self.heat_details or []):
            if row.heat_number and flt(row.qty) > 0 and not row.heat_trace_status:
                created = ensure_heat_trace_from_log_row(self, row)
                if created:
                    row.heat_trace_status = 1
