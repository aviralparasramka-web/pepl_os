import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLProductDrawing(Document):
    def validate(self):
        if not self.revisions:
            frappe.throw(_("At least one revision must be added"))

        if not self.applies_to_products:
            frappe.throw(_("At least one Product must be specified"))

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
            frappe.throw(_("Only one revision can be marked as 'Current'."))

        current = current_revisions[0]
        self.current_revision = current.revision
        self.current_file = current.drawing_file
        self.current_issue_date = current.issue_date
        self.current_customer_approved = current.customer_approved

        seen_products = set()
        for p in self.applies_to_products:
            if p.applied_product in seen_products:
                frappe.throw(_("Product {0} appears more than once").format(p.applied_product))
            seen_products.add(p.applied_product)

        seen_components = set()
        for c in self.components or []:
            if c.component_item in seen_components:
                frappe.throw(_("Component {0} appears more than once").format(c.component_item))
            seen_components.add(c.component_item)


@frappe.whitelist()
def get_drawings_for_product(product):
    """Returns all active product drawings that apply to a given product."""

    drawings = frappe.db.sql("""
        SELECT
            d.name, d.drawing_no, d.drawing_title, d.drawing_type,
            d.current_revision, d.current_file, d.current_issue_date,
            d.status
        FROM `tabPEPL Product Drawing` d
        INNER JOIN `tabPEPL Product Drawing Product` dp
            ON dp.parent = d.name
        WHERE dp.applied_product = %s
            AND d.status = 'Active'
        ORDER BY d.modified DESC
    """, product, as_dict=True)

    return drawings
