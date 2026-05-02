import frappe
from frappe import _


def execute():
    """Install or re-install the 15 PEPL RM Group records.
    Earlier fixture deployment may have failed. This patch ensures all 15
    records exist. Idempotent — safe to run multiple times.
    """

    rm_groups = [
        {"group_name": "Brass Rod", "material_base": "Brass", "default_uom": "Kg",
         "typical_wastage_percent": 5, "auto_sync_to_item_group": 1},
        {"group_name": "Brass Sheet", "material_base": "Brass", "default_uom": "Kg",
         "typical_wastage_percent": 8, "auto_sync_to_item_group": 1},
        {"group_name": "Steel Rod", "material_base": "Steel", "default_uom": "Kg",
         "typical_wastage_percent": 5, "auto_sync_to_item_group": 1},
        {"group_name": "Steel Sheet", "material_base": "Steel", "default_uom": "Kg",
         "typical_wastage_percent": 8, "auto_sync_to_item_group": 1},
        {"group_name": "Steel Forgings", "material_base": "Steel", "default_uom": "Nos",
         "typical_wastage_percent": 3, "auto_sync_to_item_group": 1},
        {"group_name": "Steel Castings", "material_base": "Steel", "default_uom": "Nos",
         "typical_wastage_percent": 3, "auto_sync_to_item_group": 1},
        {"group_name": "Aluminium Rod", "material_base": "Aluminium", "default_uom": "Kg",
         "typical_wastage_percent": 5, "auto_sync_to_item_group": 1},
        {"group_name": "Aluminium Sheet", "material_base": "Aluminium", "default_uom": "Kg",
         "typical_wastage_percent": 8, "auto_sync_to_item_group": 1},
        {"group_name": "Copper Wire", "material_base": "Copper", "default_uom": "Kg",
         "typical_wastage_percent": 3, "auto_sync_to_item_group": 1},
        {"group_name": "Hardware", "material_base": "Hardware and Fasteners", "default_uom": "Nos",
         "typical_wastage_percent": 2, "auto_sync_to_item_group": 1},
        {"group_name": "Bought-out Components", "material_base": "Bought-out Components", "default_uom": "Nos",
         "typical_wastage_percent": 0, "auto_sync_to_item_group": 1},
        {"group_name": "Plastic Components", "material_base": "Plastic", "default_uom": "Nos",
         "typical_wastage_percent": 5, "auto_sync_to_item_group": 1},
        {"group_name": "Heat Treatment", "material_base": "Process Service", "default_uom": "Nos",
         "typical_wastage_percent": 0, "auto_sync_to_item_group": 0},
        {"group_name": "Surface Treatment", "material_base": "Process Service", "default_uom": "Nos",
         "typical_wastage_percent": 0, "auto_sync_to_item_group": 0},
        {"group_name": "Tooling Amortisation", "material_base": "Other", "default_uom": "Nos",
         "typical_wastage_percent": 0, "auto_sync_to_item_group": 0},
    ]

    created = 0
    skipped = 0

    for rm in rm_groups:
        if frappe.db.exists("PEPL RM Group", rm["group_name"]):
            skipped += 1
            print(f"Skipped (exists): {rm['group_name']}")
            continue

        try:
            doc = frappe.new_doc("PEPL RM Group")
            doc.group_name = rm["group_name"]
            doc.material_base = rm["material_base"]
            doc.default_uom = rm["default_uom"]
            doc.typical_wastage_percent = rm["typical_wastage_percent"]
            doc.is_active = 1
            doc.auto_sync_to_item_group = rm["auto_sync_to_item_group"]
            doc.insert(ignore_permissions=True)

            created += 1
            print(f"Created: {rm['group_name']}")
        except Exception as e:
            print(f"Failed to create {rm['group_name']}: {str(e)}")

    frappe.db.commit()
    print(f"RM Group install complete: {created} created, {skipped} skipped")
