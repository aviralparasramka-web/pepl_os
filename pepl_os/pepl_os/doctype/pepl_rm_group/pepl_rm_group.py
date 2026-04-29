import frappe
from frappe import _
from frappe.model.document import Document


class PEPLRMGroup(Document):
    def before_save(self):
        if self.auto_sync_to_item_group and not self.linked_item_group:
            self._create_item_group()

    def _create_item_group(self):
        """Create matching Item Group under 'Raw Material' parent."""
        parent_group = "Raw Material"
        if not frappe.db.exists("Item Group", parent_group):
            parent_group = "All Item Groups"

        if frappe.db.exists("Item Group", self.group_name):
            self.linked_item_group = self.group_name
            return

        try:
            item_group = frappe.new_doc("Item Group")
            item_group.item_group_name = self.group_name
            item_group.parent_item_group = parent_group
            item_group.is_group = 0
            item_group.insert(ignore_permissions=True)
            self.linked_item_group = item_group.name

            frappe.msgprint(
                _("Auto-created Item Group: {0} under {1}").format(
                    item_group.name, parent_group
                ),
                indicator="green",
                alert=True,
            )
        except Exception as e:
            frappe.msgprint(
                _("Could not auto-create Item Group: {0}. You can create it manually later.").format(
                    str(e)
                ),
                indicator="orange",
                alert=True,
            )
