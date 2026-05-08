"""Custom field parent_category on PEPL RM Group for Item Group sync parent."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL RM Group": [
            {
                "fieldname": "parent_category",
                "label": "Parent Category",
                "fieldtype": "Select",
                "options": "Raw Material\nAdministrative Purchases\nProcess Services\nStandalone",
                "default": "Raw Material",
                "in_list_view": 1,
                "insert_after": "material_base",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
