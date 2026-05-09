# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

"""Defer bulk supplier email until PEPL Phase 2 send when selections exist."""

import frappe
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
    RequestforQuotation,
)


class PeplRequestForQuotation(RequestforQuotation):
    def on_submit(self):
        self.db_set("status", "Submitted")
        for supplier in self.suppliers:
            supplier.email_sent = 0
            supplier.quote_status = "Pending"

        meta = frappe.get_meta("Request for Quotation")
        if meta.has_field("per_item_vendor_selections") and (
            self.get("per_item_vendor_selections") or []
        ):
            return

        self.send_to_supplier()
