"""Patch: rate_source audit field on PEPL CST Component."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL CST Component": [
            {
                "fieldname": "rate_source",
                "label": "Rate Source",
                "fieldtype": "Data",
                "insert_after": "component_subtotal",
                "read_only": 1,
                "description": "Audit trail of rate determination",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
