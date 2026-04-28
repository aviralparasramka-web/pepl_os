import frappe
from frappe import _
from frappe.model.document import Document


class PEPLProductDrawing(Document):
    def validate(self):
        if self.linked_product:
            product_type = frappe.db.get_value(
                "Item", self.linked_product, "custom_product_type"
            )
            if product_type and product_type == "Single Component":
                frappe.msgprint(
                    _("Item {0} is marked as 'Single Component'. Product Drawings are typically for Assemblies. Use PEPL Item Drawing instead, or change the item's product type.").format(
                        self.linked_product
                    ),
                    indicator="orange",
                    alert=True
                )

        if self.status == "Active":
            existing = frappe.db.get_all(
                "PEPL Product Drawing",
                filters={
                    "linked_product": self.linked_product,
                    "drawing_no": self.drawing_no,
                    "status": "Active",
                    "name": ["!=", self.name]
                },
                fields=["name", "revision"]
            )
            if existing:
                frappe.msgprint(
                    _("Another active revision exists for this drawing: {0} (Rev {1}). Consider marking it as Superseded.").format(
                        existing[0].name, existing[0].revision
                    ),
                    indicator="orange",
                    alert=True
                )

        if self.components:
            seen_items = set()
            for c in self.components:
                if c.component_item in seen_items:
                    frappe.throw(_(
                        "Component item {0} appears more than once. Combine into one row with summed quantity."
                    ).format(c.component_item))
                seen_items.add(c.component_item)


@frappe.whitelist()
def get_active_drawing_for_product(product_item):
    """Returns the current active product drawing for a given item.
    Used by Tender Management, Sales Order to fetch the right drawing."""

    drawing = frappe.db.get_value(
        "PEPL Product Drawing",
        {"linked_product": product_item, "status": "Active"},
        ["name", "drawing_no", "revision", "drawing_file", "issue_date"],
        as_dict=True
    )
    return drawing
