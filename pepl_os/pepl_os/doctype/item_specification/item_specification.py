import frappe
from frappe import _
from frappe.model.document import Document


class ItemSpecification(Document):
    def validate(self):
        if not self.file_attach and not self.spec_text:
            frappe.msgprint(
                _("Specification {0} has neither a file nor text content. Consider adding one.").format(
                    self.spec_title
                ),
                indicator="orange",
                alert=True
            )
