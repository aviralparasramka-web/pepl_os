import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PEPLPSDTracker(Document):
    def validate(self):
        if self.linked_sales_order and not self.sector:
            self._fetch_sector_from_so()

        if self.psd_entries:
            self.active_entries_count = sum(
                1 for e in self.psd_entries
                if e.psd_status not in ["Closed", "PSD Not Required"]
            )
            self.total_psd_amount = sum(flt(e.psd_amount) for e in self.psd_entries)
        else:
            self.active_entries_count = 0
            self.total_psd_amount = 0

        if not self.tracker_id:
            self.tracker_id = self.name

    def _fetch_sector_from_so(self):
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
def create_psd_tracker_for_so(sales_order_name):
    """Create one PSD Tracker per Sales Order with one default PSD Entry.
    Idempotent — returns existing tracker if already created.
    """
    existing = frappe.db.exists("PEPL PSD Tracker", {"linked_sales_order": sales_order_name})
    if existing:
        return {"created": False, "tracker_name": existing}

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
    initial_amount = flt(so.grand_total) * default_percent / 100
    initial_status = "Pending" if default_percent > 0 else "PSD Not Required"

    tracker = frappe.new_doc("PEPL PSD Tracker")
    tracker.linked_sales_order = so.name
    tracker.customer = so.customer
    tracker.sector = sector

    tracker.append("psd_entries", {
        "entry_label": "Initial PSD",
        "psd_status": initial_status,
        "psd_percent": default_percent,
        "psd_amount": initial_amount,
        "order_value_basis": so.grand_total
    })

    tracker.insert(ignore_permissions=True)

    return {
        "created": True,
        "tracker_name": tracker.name,
        "sector": sector,
        "percentage": default_percent,
        "initial_amount": initial_amount
    }
