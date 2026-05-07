"""
Patch: Product Readiness collapsible section + HTML panel on Sales Order.
Idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "product_readiness_section",
                "label": "Product Readiness",
                "fieldtype": "Section Break",
                "insert_after": "items",
                "collapsible": 1,
            },
            {
                "fieldname": "product_readiness_html",
                "label": "",
                "fieldtype": "HTML",
                "insert_after": "product_readiness_section",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
