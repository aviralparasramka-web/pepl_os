"""Custom field: Item Name (fetch from Item) on PEPL CST Component grid."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL CST Component": [
            {
                "fieldname": "item_name_display",
                "label": "Item Name",
                "fieldtype": "Data",
                "read_only": 1,
                "fetch_from": "component_item.item_name",
                "in_list_view": 1,
                "insert_after": "component_item",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
