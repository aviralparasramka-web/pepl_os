import frappe
from frappe import _
from frappe.model.document import Document


class PEPLItemDrawing(Document):
    def validate(self):
        if self.status == "Active":
            existing = frappe.db.get_all(
                "PEPL Item Drawing",
                filters={
                    "linked_item": self.linked_item,
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


@frappe.whitelist()
def get_active_drawing_for_item(item):
    """Returns the current active item drawing for a given item."""

    drawing = frappe.db.get_value(
        "PEPL Item Drawing",
        {"linked_item": item, "status": "Active"},
        ["name", "drawing_no", "revision", "drawing_file", "issue_date"],
        as_dict=True
    )
    return drawing
