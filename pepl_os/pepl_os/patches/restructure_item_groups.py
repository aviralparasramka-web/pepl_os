"""
Patch: Restructure Item Groups per PEPL Purchase Module Architecture v1.0
- Rename "Capital Goods" -> "Machinery"
- Add new top-level groups: Tools, Dies & Patterns, Fixtures, Gauges,
  Instruments, Miscellaneous
- Add "Castings" sub-group under Raw Material
- Idempotent: safe to run multiple times
"""

import frappe


def execute():
    # 1. Rename Capital Goods -> Machinery (if not already done)
    if frappe.db.exists("Item Group", "Capital Goods") \
       and not frappe.db.exists("Item Group", "Machinery"):
        frappe.rename_doc(
            "Item Group", "Capital Goods", "Machinery", merge=False
        )
        frappe.db.commit()

    # 2. Create Machinery if Capital Goods never existed (fresh install case)
    if not frappe.db.exists("Item Group", "Machinery"):
        _create_top_level("Machinery")

    # 3. Create new top-level Item Groups
    new_groups = [
        "Tools",
        "Dies & Patterns",
        "Fixtures",
        "Gauges",
        "Instruments",
        "Miscellaneous",
    ]
    for name in new_groups:
        if not frappe.db.exists("Item Group", name):
            _create_top_level(name)

    # 4. Add Castings sub-group under Raw Material
    if frappe.db.exists("Item Group", "Raw Material") \
       and not frappe.db.exists("Item Group", "Castings"):
        ig = frappe.new_doc("Item Group")
        ig.item_group_name = "Castings"
        ig.parent_item_group = "Raw Material"
        ig.is_group = 0
        ig.insert(ignore_permissions=True)

    frappe.db.commit()


def _create_top_level(name):
    ig = frappe.new_doc("Item Group")
    ig.item_group_name = name
    ig.parent_item_group = "All Item Groups"
    ig.is_group = 0
    ig.insert(ignore_permissions=True)
