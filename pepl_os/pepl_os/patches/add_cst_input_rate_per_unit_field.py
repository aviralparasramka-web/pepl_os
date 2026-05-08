"""Custom field: Per-Unit Rate on PEPL CST Component (rate × qty → cost on validate)."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL CST Component": [
            {
                "fieldname": "input_rate_per_unit",
                "label": "Per-Unit Rate",
                "fieldtype": "Currency",
                "options": "INR",
                "in_list_view": 1,
                "insert_after": "quantity_per_assembly",
                "description": (
                    "Enter per-unit rate (₹/unit). Cost auto-calculated "
                    "as rate × Qty per Assembly on save."
                ),
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
