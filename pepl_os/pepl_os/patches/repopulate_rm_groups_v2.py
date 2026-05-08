"""Phase C3: wipe PEPL RM Groups (test data) and insert v2 catalog (38 rows)."""

import frappe

RM_DEFS = [
    # Raw Material — metal form (20)
    ("Aluminium Sheet and Plate", "Raw Material", "Aluminium", "Kg", 8),
    ("Aluminium Rod", "Raw Material", "Aluminium", "Kg", 5),
    ("Aluminium Tube and Section", "Raw Material", "Aluminium", "Kg", 5),
    ("Aluminium Forging", "Raw Material", "Aluminium", "Nos", 3),
    ("Aluminium Casting", "Raw Material", "Aluminium", "Nos", 3),
    ("Brass Sheet and Plate", "Raw Material", "Brass", "Kg", 8),
    ("Brass Rod", "Raw Material", "Brass", "Kg", 5),
    ("Brass Tube and Section", "Raw Material", "Brass", "Kg", 5),
    ("Brass Forging", "Raw Material", "Brass", "Nos", 3),
    ("Brass Casting", "Raw Material", "Brass", "Nos", 3),
    ("Steel Sheet and Plate", "Raw Material", "Steel", "Kg", 8),
    ("Steel Rod", "Raw Material", "Steel", "Kg", 5),
    ("Steel Tube and Section", "Raw Material", "Steel", "Kg", 5),
    ("Steel Forging", "Raw Material", "Steel", "Nos", 3),
    ("Steel Casting", "Raw Material", "Steel", "Nos", 3),
    ("Copper Sheet and Plate", "Raw Material", "Copper", "Kg", 8),
    ("Copper Rod", "Raw Material", "Copper", "Kg", 5),
    ("Copper Tube and Section", "Raw Material", "Copper", "Kg", 5),
    ("Copper Forging", "Raw Material", "Copper", "Nos", 3),
    ("Copper Casting", "Raw Material", "Copper", "Nos", 3),
    # Raw Material — non-metal (4)
    ("Hardware and Fasteners", "Raw Material", "Hardware", "Nos", 2),
    ("Plastic and Rubber Items", "Raw Material", "Plastic-Rubber", "Nos", 5),
    ("Packaging Material", "Raw Material", "Packaging", "Nos", 2),
    ("BOQ", "Raw Material", "Bought Out", "Nos", 0),
    # Administrative Purchases (5)
    ("Computers and Peripherals", "Administrative Purchases", "IT Hardware", "Nos", 0),
    ("Electricals", "Administrative Purchases", "Electrical", "Nos", 0),
    ("Electrical Fittings", "Administrative Purchases", "Electrical", "Nos", 0),
    ("Consumables", "Administrative Purchases", "Consumable", "Nos", 0),
    ("Tooling and Inserts", "Administrative Purchases", "Tooling", "Nos", 0),
    # Process Services (3)
    ("Heat Treatment", "Process Services", "Process Service", "Nos", 0),
    ("Surface Treatment", "Process Services", "Process Service", "Nos", 0),
    ("Tooling Amortisation", "Process Services", "Process Service", "Nos", 0),
    # Standalone (6)
    ("Tool Instruments", "Standalone", "Tool", "Nos", 0),
    ("Dies & Patterns", "Standalone", "Tooling", "Nos", 0),
    ("Fixtures", "Standalone", "Tooling", "Nos", 0),
    ("Gauges", "Standalone", "Inspection", "Nos", 0),
    ("Instruments", "Standalone", "Inspection", "Nos", 0),
    ("Machinery", "Standalone", "Capital", "Nos", 0),
]


def execute():
    frappe.db.sql("UPDATE `tabPEPL CST Component` SET rm_group=NULL WHERE rm_group IS NOT NULL")

    for name in frappe.get_all("PEPL RM Group", pluck="name"):
        try:
            frappe.delete_doc("PEPL RM Group", name, force=True, ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"RM Group delete failed: {name}")

    created = 0
    failed = []
    missing_link = []

    for gn, pcat, base, uom, wastage in RM_DEFS:
        try:
            if frappe.db.exists("PEPL RM Group", gn):
                continue
            d = frappe.new_doc("PEPL RM Group")
            d.group_name = gn
            d.material_base = base
            d.parent_category = pcat
            d.default_uom = uom
            d.typical_wastage_percent = wastage
            d.is_active = 1
            d.auto_sync_to_item_group = 1
            d.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            failed.append(f"{gn}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), f"RM Group insert failed: {gn}")

    frappe.db.commit()

    for gn, _, _, _, _ in RM_DEFS:
        li = frappe.db.get_value("PEPL RM Group", gn, "linked_item_group")
        if not li:
            missing_link.append(gn)

    frappe.log_error(
        "RM Group repopulate v2 complete.\n"
        f"Created: {created}\nFailed: {failed}\nMissing linked_item_group: {missing_link}",
        "PEPL RM Group Repopulate v2",
    )
    frappe.db.commit()
