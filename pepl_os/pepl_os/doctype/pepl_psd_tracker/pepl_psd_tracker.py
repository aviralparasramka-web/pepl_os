import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months


class PEPLPSDTracker(Document):
    def validate(self):
        if self.linked_sales_order and not self.sector:
            self._fetch_sector_from_so()

        if self.order_value and self.psd_percentage is not None:
            calculated_amount = flt(self.order_value) * flt(self.psd_percentage) / 100
            if not self.psd_amount or flt(self.psd_amount) == 0:
                self.psd_amount = calculated_amount

        if flt(self.psd_percentage) == 0 and self.psd_status == "Pending":
            self.psd_status = "PSD Not Required"

        if self.last_supply_date and not self.expected_refund_date:
            self.expected_refund_date = add_months(getdate(self.last_supply_date), 14)

        if self.last_supply_date and not self.supply_completed:
            self.supply_completed = 1

    def _fetch_sector_from_so(self):
        if not self.linked_sales_order:
            return
        customer = frappe.db.get_value("Sales Order", self.linked_sales_order, "customer")
        if not customer:
            return
        cg = frappe.db.get_value("Customer", customer, "customer_group")
        if not cg:
            return
        if "Railways" in cg:
            self.sector = "Railways"
        elif "Defence" in cg:
            self.sector = "Defence"
        elif "Private" in cg:
            self.sector = "Private"
        else:
            self.sector = "Others"


@frappe.whitelist()
def create_psd_for_sales_order(sales_order_name):
    """Auto-create PSD Tracker for a Sales Order.
    Called from SO on_submit hook.
    """
    existing = frappe.db.exists("PEPL PSD Tracker", {"linked_sales_order": sales_order_name})
    if existing:
        return {"created": False, "existing": existing}

    so = frappe.get_doc("Sales Order", sales_order_name)

    sector = "Others"
    if so.customer:
        cg = frappe.db.get_value("Customer", so.customer, "customer_group")
        if cg:
            if "Railways" in cg:
                sector = "Railways"
            elif "Defence" in cg:
                sector = "Defence"
            elif "Private" in cg:
                sector = "Private"

    default_percent = 5 if sector == "Defence" else 0

    psd = frappe.new_doc("PEPL PSD Tracker")
    psd.linked_sales_order = so.name
    psd.customer = so.customer
    psd.sector = sector
    psd.order_value = so.grand_total
    psd.psd_percentage = default_percent
    psd.psd_amount = flt(so.grand_total) * default_percent / 100
    psd.psd_status = "Pending" if default_percent > 0 else "PSD Not Required"
    psd.insert(ignore_permissions=True)

    return {
        "created": True,
        "psd_name": psd.name,
        "sector": sector,
        "percentage": default_percent,
        "amount": psd.psd_amount
    }
