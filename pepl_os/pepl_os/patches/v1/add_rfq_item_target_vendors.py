"""
Patch: Add target_vendors Table MultiSelect field on Request for Quotation Item.

Idempotent — create_custom_fields with update=True.
Requires PEPL RFQ Item Target Vendor DocType to be synced first (post_model_sync).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    frappe.reload_doctype("Request for Quotation Item", force=True)

    custom_fields = {
        "Request for Quotation Item": [
            {
                "fieldname": "target_vendors",
                "label": "Target Vendors",
                "fieldtype": "Table MultiSelect",
                "options": "PEPL RFQ Item Target Vendor",
                "insert_after": "description",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
