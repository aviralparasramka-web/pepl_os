import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months


class PEPLPSDEntry(Document):
    def validate(self):
        if self.order_value_basis and self.psd_percent is not None:
            calculated = flt(self.order_value_basis) * flt(self.psd_percent) / 100
            if not self.psd_amount or flt(self.psd_amount) == 0:
                self.psd_amount = calculated

        if flt(self.psd_percent) == 0 and self.psd_status == "Pending":
            self.psd_status = "PSD Not Required"

        if self.last_supply_date and not self.expected_refund_date:
            self.expected_refund_date = add_months(getdate(self.last_supply_date), 14)
