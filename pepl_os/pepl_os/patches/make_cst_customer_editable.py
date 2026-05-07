"""Force PEPL CST Cost Sheet Customer field editable (overrides Property Setter if present)."""

import frappe


def execute():
    frappe.make_property_setter(
        {
            "doctype": "PEPL CST Cost Sheet",
            "doctype_or_field": "DocField",
            "fieldname": "customer",
            "property": "read_only",
            "value": "0",
            "property_type": "Check",
        },
        validate_fields_for_doctype=False,
    )
    frappe.db.commit()
