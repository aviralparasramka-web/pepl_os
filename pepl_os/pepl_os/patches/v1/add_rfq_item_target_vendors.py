"""
Patch: Add target_vendors Table MultiSelect field on Request for Quotation Item.

Idempotent — create_custom_fields with update=True.
Requires PEPL RFQ Item Target Vendor DocType to be synced first (post_model_sync).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # Defensive prefix per V4 closing rule.
    # Forces DocType schema to be loaded from disk into
    # DB before validation runs. Makes patch
    # order-independent and safe to run in either
    # pre_model_sync or post_model_sync.
    try:
        frappe.reload_doctype("PEPL RFQ Item Target Vendor", force=True)
        frappe.reload_doctype("Request for Quotation Item", force=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"reload_doctype failed: {e}",
            "add_rfq_item_target_vendors",
        )

    # ... existing patch logic continues unchanged ...
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
