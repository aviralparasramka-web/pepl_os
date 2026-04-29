import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PEPLCSTComponent(Document):
    def validate(self):
        if self.manufactured_or_bought_out == "Manufactured":
            self.component_subtotal = (
                flt(self.raw_material_cost)
                + flt(self.machining_cost)
                + flt(self.surface_treatment_cost)
                + flt(self.component_other_charges)
            )
            self.bought_out_cost = 0
        elif self.manufactured_or_bought_out == "Bought Out":
            self.component_subtotal = (
                flt(self.bought_out_cost)
                + flt(self.surface_treatment_cost)
                + flt(self.component_other_charges)
            )
            self.raw_material_cost = 0
            self.machining_cost = 0
