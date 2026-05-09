"""
Patch: Add PEPL per-item RFQ vendor selection child table field on RFQ.

Idempotent — create_custom_fields with update=True.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Request for Quotation": [
            {
                "fieldname": "per_item_vendor_selections_section",
                "label": "PEPL Per-item Vendors",
                "fieldtype": "Section Break",
                "insert_after": "suppliers",
                "collapsible": 1,
                "description": (
                    "Select which vendors receive each RFQ line. Phase 2 email send "
                    "aggregates items by supplier when this table has rows."
                ),
            },
            {
                "fieldname": "per_item_vendor_selections",
                "label": "Per-item Vendor Selections",
                "fieldtype": "Table",
                "options": "PEPL RFQ Item Vendor Selection",
                "insert_after": "per_item_vendor_selections_section",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
