"""
Patch: Add Purchase Module custom fields to Item DocType (Day 2 Purchase MVP)
- item_category (Select, 11 options matching top-level Item Groups)
- is_tool (Check)
- is_consumable (Check)
- expected_life_units (Int, depends on is_tool or is_consumable)
- Idempotent: uses create_custom_fields with update=True
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    item_category_options = "\n".join([
        "",
        "Tools",
        "Dies & Patterns",
        "Fixtures",
        "Gauges",
        "Raw Material",
        "Instruments",
        "Machinery",
        "Consumables",
        "Services",
        "Finished Goods",
        "Miscellaneous",
    ])

    custom_fields = {
        "Item": [
            {
                "fieldname": "item_category",
                "label": "Item Category",
                "fieldtype": "Select",
                "options": item_category_options,
                "insert_after": "item_group",
                "description": (
                    "PEPL top-level category for reporting and filtering. "
                    "Mirrors top-level Item Groups."
                ),
            },
            {
                "fieldname": "is_tool",
                "label": "Is Tool",
                "fieldtype": "Check",
                "insert_after": "is_fixed_asset",
                "description": (
                    "Tick if this item is a tool (cutting tool, "
                    "drill bit, measuring tool, etc.)."
                ),
            },
            {
                "fieldname": "is_consumable",
                "label": "Is Consumable",
                "fieldtype": "Check",
                "insert_after": "is_tool",
                "description": (
                    "Tick if this item is a consumable "
                    "(cutting fluid, coolant, abrasive, packaging, etc.)."
                ),
            },
            {
                "fieldname": "expected_life_units",
                "label": "Expected Life (Units)",
                "fieldtype": "Int",
                "insert_after": "is_consumable",
                "depends_on": "eval:doc.is_tool || doc.is_consumable",
                "description": (
                    "Expected number of components produced before "
                    "replacement. Used for tool/consumable performance "
                    "analysis in Phase 8."
                ),
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
