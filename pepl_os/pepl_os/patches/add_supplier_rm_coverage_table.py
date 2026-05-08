"""Child table rm_coverage on PEPL Supplier Approval."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "PEPL Supplier Approval": [
            {
                "fieldname": "rm_coverage",
                "label": "RM Coverage",
                "fieldtype": "Table",
                "options": "PEPL Supplier RM Coverage",
                "insert_after": "approval_status",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
