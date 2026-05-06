"""
Patch: Add a Custom HTML field on Material Request to host the
Stock & Pipeline dashboard panel rendered by the JS file
material_request_dashboard.js.
Idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Material Request": [
            {
                "fieldname": "pepl_supply_dashboard_section",
                "label": "Stock & Pipeline Position",
                "fieldtype": "Section Break",
                "insert_after": "auto_drafted",
                "collapsible": 0,
            },
            {
                "fieldname": "pepl_supply_dashboard_html",
                "label": "",
                "fieldtype": "HTML",
                "insert_after": "pepl_supply_dashboard_section",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
