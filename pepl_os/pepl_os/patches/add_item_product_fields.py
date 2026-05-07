"""Patch: Add Item drawing, PL, sector, is_product, and product_type fields."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Item": [
            {
                "fieldname": "drawing_no",
                "label": "Drawing No",
                "fieldtype": "Data",
                "insert_after": "item_name",
            },
            {
                "fieldname": "drawing_rev",
                "label": "Drawing Rev",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "drawing_no",
            },
            {
                "fieldname": "pl_no",
                "label": "PL No",
                "fieldtype": "Data",
                "insert_after": "drawing_rev",
                "description": "Parts List number for Railways items",
            },
            {
                "fieldname": "sector",
                "label": "Sector",
                "fieldtype": "Select",
                "options": "\nRailways\nDefence\nPrivate\nOthers",
                "insert_after": "pl_no",
            },
            {
                "fieldname": "is_product",
                "label": "Is Product (Sold to Customer)",
                "fieldtype": "Check",
                "insert_after": "sector",
                "description": "Tick if PEPL sells this as a product. Triggers MR auto-draft on SO submit.",
            },
            {
                "fieldname": "product_type",
                "label": "Product Type",
                "fieldtype": "Select",
                "options": "\nSingle Component\nAssembly\nSub-Assembly",
                "depends_on": "eval:doc.is_product",
                "insert_after": "is_product",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
