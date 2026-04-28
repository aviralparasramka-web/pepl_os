import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLItemDrawing(Document):
    def validate(self):
        if not self.revisions:
            frappe.throw(_("At least one revision must be added"))

        if not self.applies_to_items:
            frappe.throw(_("At least one Item must be specified in 'Items This Drawing Applies To'"))

        current_revisions = [r for r in self.revisions if r.is_current]

        if len(current_revisions) == 0:
            sorted_revs = sorted(
                self.revisions,
                key=lambda r: getdate(r.issue_date) if r.issue_date else getdate("1900-01-01"),
                reverse=True
            )
            sorted_revs[0].is_current = 1
            current_revisions = [sorted_revs[0]]
            frappe.msgprint(
                _("Auto-marked the most recent revision as current."),
                indicator="blue",
                alert=True
            )

        if len(current_revisions) > 1:
            frappe.throw(_("Only one revision can be marked as 'Current'. Please untick the others."))

        current = current_revisions[0]
        self.current_revision = current.revision
        self.current_file = current.drawing_file
        self.current_issue_date = current.issue_date
        self.current_customer_approved = current.customer_approved

        seen = set()
        for item_row in self.applies_to_items:
            if item_row.applied_item in seen:
                frappe.throw(_("Item {0} appears more than once").format(item_row.applied_item))
            seen.add(item_row.applied_item)


@frappe.whitelist()
def get_drawings_for_item(item):
    """Returns all active item drawings that apply to a given item."""

    drawings = frappe.db.sql("""
        SELECT
            d.name, d.drawing_no, d.drawing_title, d.category,
            d.current_revision, d.current_file, d.current_issue_date,
            d.status
        FROM `tabPEPL Item Drawing` d
        INNER JOIN `tabPEPL Item Drawing Item` di
            ON di.parent = d.name
        WHERE di.applied_item = %s
            AND d.status = 'Active'
        ORDER BY d.modified DESC
    """, item, as_dict=True)

    return drawings
