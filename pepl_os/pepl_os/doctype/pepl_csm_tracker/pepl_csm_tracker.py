# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# PEPL CSM Tracker — parent controller

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PEPLCSMTracker(Document):
    def validate(self):
        self._update_consumption_weight_status()
        self._compute_reconciliation()

    def _update_consumption_weight_status(self):
        """Set weight_status and weight_variance on each Consumption row."""
        for row in (self.consumption or []):
            cust = flt(row.received_weight_customer)
            pepl = flt(row.dispatched_weight_pepl)
            if cust:
                row.weight_variance = cust - pepl
                if abs(row.weight_variance) <= 0.001:
                    row.weight_status = "Confirmed"
                else:
                    row.weight_status = "Confirmed"  # Variance is fine; customer just weighed differently
            else:
                row.weight_variance = 0
                row.weight_status = "Pending Customer Confirmation"

    def _compute_reconciliation(self):
        """Aggregate receipts / consumption / returns into summary fields."""
        total_recv = sum(flt(r.qty_received) for r in (self.receipts or []))
        total_pepl = sum(flt(r.dispatched_weight_pepl) for r in (self.consumption or []))
        total_cust = sum(flt(r.received_weight_customer) for r in (self.consumption or []) if flt(r.received_weight_customer))
        total_effective = sum(
            flt(r.received_weight_customer) if flt(r.received_weight_customer) else flt(r.dispatched_weight_pepl)
            for r in (self.consumption or [])
        )
        total_ret_scrap = sum(
            flt(r.qty_returned) for r in (self.returns or [])
            if r.return_type == "Scrap return"
        )
        total_ret_rej = sum(
            flt(r.qty_returned) for r in (self.returns or [])
            if r.return_type == "Rejected pieces return"
        )
        allowed_loss = total_recv * flt(self.allowed_loss_pct) / 100.0
        pending_rows = sum(
            1 for r in (self.consumption or [])
            if not flt(r.received_weight_customer)
        )

        balance = total_recv - total_effective - total_ret_scrap - total_ret_rej - allowed_loss

        self.total_received = total_recv
        self.total_dispatched_weight_pepl = total_pepl
        self.total_dispatched_weight_customer = total_cust
        self.total_dispatched_weight_effective = total_effective
        self.total_returned_scrap = total_ret_scrap
        self.total_returned_rejected = total_ret_rej
        self.allowed_loss_qty = allowed_loss
        self.balance_unaccounted = balance
        self.rows_pending_customer_confirmation = pending_rows

        # threshold: 0.5% of total_received OR 1 unit, whichever larger
        threshold = max(total_recv * 0.005, 1.0) if total_recv else 0.001
        balance_ok = abs(balance) <= threshold

        if pending_rows > 0:
            self.reconciliation_status = "Pending Customer Confirmation"
        elif balance_ok:
            self.reconciliation_status = "Reconciled"
        else:
            self.reconciliation_status = "Mismatch"
