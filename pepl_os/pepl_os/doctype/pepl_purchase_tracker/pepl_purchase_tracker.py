# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, getdate, today


class PEPLPurchaseTracker(Document):
    def validate(self):
        self._calculate_ageing()
        self._auto_set_status()

    def _calculate_ageing(self):
        if self.current_status == "Closed":
            self.days_outstanding = 0
            self.ageing_bucket = "Closed"
            return

        if not self.po_date:
            self.days_outstanding = 0
            self.ageing_bucket = "0-7 days"
            return

        d = date_diff(getdate(today()), getdate(self.po_date))
        self.days_outstanding = max(0, int(d))

        if self.days_outstanding <= 7:
            self.ageing_bucket = "0-7 days"
        elif self.days_outstanding <= 15:
            self.ageing_bucket = "8-15 days"
        elif self.days_outstanding <= 30:
            self.ageing_bucket = "16-30 days"
        else:
            self.ageing_bucket = "30+ days"

    def _auto_set_status(self):
        if self.current_status == "Closed":
            return

        if self.grn_reference:
            if self.inspection_status == "Pass":
                self.current_status = "Inspected - Pass"
                return
            if self.inspection_status == "Fail":
                self.current_status = "Inspected - Fail"
                return
            if self.inspection_status == "Partial":
                self.current_status = "Received"
                return
            self.current_status = "Received"
            return

        if self.dispatch_date:
            self.current_status = "Material Dispatched"
            return

        if self.acknowledgment_date:
            self.current_status = "Acknowledged"
            return

        self.current_status = "PO Sent"


def update_all_purchase_trackers_daily():
    """Recalculate ageing for trackers that are still open."""
    names = frappe.get_all(
        "PEPL Purchase Tracker",
        filters={"current_status": ["!=", "Closed"]},
        pluck="name",
    )
    for name in names:
        try:
            doc = frappe.get_doc("PEPL Purchase Tracker", name)
            doc._calculate_ageing()
            frappe.db.set_value(
                "PEPL Purchase Tracker",
                name,
                {
                    "days_outstanding": doc.days_outstanding,
                    "ageing_bucket": doc.ageing_bucket,
                },
                update_modified=False,
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Purchase Tracker daily ageing")
