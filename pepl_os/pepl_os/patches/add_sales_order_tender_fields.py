"""Patch: Link Sales Order to PEPL Tender with derived NIT and sector."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "linked_tender",
                "label": "Linked Tender",
                "fieldtype": "Link",
                "options": "PEPL Tender",
                "insert_after": "po_no",
            },
            {
                "fieldname": "nit_number",
                "label": "NIT Number",
                "fieldtype": "Data",
                "read_only": 1,
                "fetch_from": "linked_tender.nit_number",
                "insert_after": "linked_tender",
            },
            {
                "fieldname": "sector",
                "label": "Sector",
                "fieldtype": "Select",
                "options": "\nRailways\nDefence\nPrivate\nOthers",
                "read_only": 1,
                "fetch_from": "linked_tender.sector",
                "insert_after": "nit_number",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
