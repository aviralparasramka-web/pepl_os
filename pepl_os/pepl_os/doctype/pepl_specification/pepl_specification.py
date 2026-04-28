import frappe
from frappe import _
from frappe.model.document import Document


class PEPLSpecification(Document):
    def validate(self):
        if self.status != "Draft" and not self.spec_file and not self.spec_text:
            frappe.msgprint(
                _("Specification {0} has neither a file nor text content. Add one before activating.").format(
                    self.spec_title
                ),
                indicator="orange",
                alert=True
            )


@frappe.whitelist()
def get_specs_for_item(item):
    """Returns all active specifications applied to a given item.
    Used by Item form to display the Specifications tab."""

    specs = frappe.db.sql("""
        SELECT
            spec.name, spec.spec_title, spec.spec_type,
            spec.reference_no, spec.issuing_authority,
            spec.status, spec.spec_file, spec.issue_date,
            app.applies_to_type, app.is_primary
        FROM `tabPEPL Specification` spec
        INNER JOIN `tabPEPL Specification Application` app
            ON app.parent = spec.name
        WHERE app.applied_item = %s
            AND spec.status = 'Active'
        ORDER BY app.is_primary DESC, spec.modified DESC
    """, item, as_dict=True)

    return specs
