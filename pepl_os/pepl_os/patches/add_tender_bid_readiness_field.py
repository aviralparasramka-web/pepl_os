"""
Patch: Bid Readiness collapsible section + HTML panel on PEPL Tender.
Idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL Tender": [
            {
                "fieldname": "bid_readiness_section",
                "label": "Bid Readiness",
                "fieldtype": "Section Break",
                "insert_after": "so_status_display",
                "collapsible": 1,
            },
            {
                "fieldname": "bid_readiness_html",
                "label": "",
                "fieldtype": "HTML",
                "insert_after": "bid_readiness_section",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
