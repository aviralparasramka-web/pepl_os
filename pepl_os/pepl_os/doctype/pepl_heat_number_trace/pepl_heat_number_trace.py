# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# PEPL Heat Number Trace — parent controller

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PEPLHeatNumberTrace(Document):
    def validate(self):
        self._compute_totals()
        self._compute_status()

    def _compute_totals(self):
        totals = {
            "Received": 0,
            "Issued to Production": 0,
            "Returned": 0,
            "Scrapped": 0,
            "Dispatched to Customer": 0,
        }
        for entry in (self.usage_log or []):
            if entry.event_type in totals:
                totals[entry.event_type] += flt(entry.qty)

        self.total_qty_received = totals["Received"]
        self.total_qty_consumed = totals["Issued to Production"]
        self.total_qty_returned = totals["Returned"]
        self.total_qty_scrapped = totals["Scrapped"]
        self.total_qty_dispatched = totals["Dispatched to Customer"]

        # Available = received + returned - consumed - scrapped - dispatched
        self.current_qty_available = (
            self.total_qty_received
            + self.total_qty_returned
            - self.total_qty_consumed
            - self.total_qty_scrapped
            - self.total_qty_dispatched
        )

    def _compute_status(self):
        if flt(self.current_qty_available) <= 0.001:
            if flt(self.total_qty_dispatched) > 0:
                self.current_status = "Fully Dispatched"
            elif flt(self.total_qty_scrapped) > 0 and flt(self.total_qty_consumed) == 0:
                self.current_status = "Scrapped"
            else:
                self.current_status = "Fully Consumed"
        elif flt(self.total_qty_consumed) > 0:
            self.current_status = "In Production"
        else:
            self.current_status = "Available"
