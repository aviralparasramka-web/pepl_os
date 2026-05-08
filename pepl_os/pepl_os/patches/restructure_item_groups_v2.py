"""
Phase B: Item Group restructure v2 (test-data aggressive migration).

Creates canonical parents/leaves, migrates Tools → Tool Instruments,
preserves Finished Goods subtree, reparents stray items to Miscellaneous,
deletes obsolete leaf groups. Logs summary to Error Log / Activity Log.
"""

import frappe
from frappe import _


ROOT = "All Item Groups"
RAW = "Raw Material"
MISC = "Miscellaneous"
ADM = "Administrative Purchases"
PROC = "Process Services"


NEW_RAW_LEAVES = [
    "Aluminium Sheet and Plate",
    "Aluminium Rod",
    "Aluminium Tube and Section",
    "Aluminium Forging",
    "Aluminium Casting",
    "Brass Sheet and Plate",
    "Brass Rod",
    "Brass Tube and Section",
    "Brass Forging",
    "Brass Casting",
    "Steel Sheet and Plate",
    "Steel Rod",
    "Steel Tube and Section",
    "Steel Forging",
    "Steel Casting",
    "Copper Sheet and Plate",
    "Copper Rod",
    "Copper Tube and Section",
    "Copper Forging",
    "Copper Casting",
    "Hardware and Fasteners",
    "Plastic and Rubber Items",
    "Packaging Material",
    "BOQ",
]

NEW_ADMIN_LEAVES = [
    "Computers and Peripherals",
    "Electricals",
    "Electrical Fittings",
    "Consumables",
    "Tooling and Inserts",
]

NEW_PROCESS_LEAVES = [
    "Heat Treatment",
    "Surface Treatment",
    "Tooling Amortisation",
]

NEW_STANDALONE_LEAVES = [
    "Tool Instruments",
    "Dies & Patterns",
    "Fixtures",
    "Gauges",
    "Instruments",
    "Machinery",
    "Services",
]

FINISHED_GOODS_CHILDREN = [
    "Railway Components",
    "Defence Components",
    "Private Sector Components",
]

# Explicit obsolete names only — must NOT overlap NEW_* leaf names (single global Item Group name per ERPNext)
LEGACY_PURGE_NAMES = set(
    [
        "Plates and Sheets",
        "Bars and Rods",
        "Forgings",
        "Castings",
        "Bought Outs",
        "Bought Out Items",
        "Fasteners",
        "Bought-out Components",
        "Brass Sheet",
        "Steel Sheet",
        "Steel Forgings",
        "Steel Castings",
        "Aluminium Sheet",
        "Copper Wire",
        "Hardware",
        "Plastic Components",
        "Capital Goods",
        "Tools",
    ]
)


def _ensure_item_group(name, parent, is_group=0):
    if frappe.db.exists("Item Group", name):
        doc = frappe.get_doc("Item Group", name)
        if doc.parent_item_group != parent and name not in (ROOT, RAW, MISC, ADM, PROC):
            doc.db_set("parent_item_group", parent, update_modified=False)
        if doc.is_group != is_group:
            doc.db_set("is_group", is_group, update_modified=False)
        return False
    ig = frappe.new_doc("Item Group")
    ig.item_group_name = name
    ig.parent_item_group = parent
    ig.is_group = is_group
    ig.insert(ignore_permissions=True)
    return True


def _move_items_to_misc(from_group, misc_name):
    cnt = frappe.db.count("Item", {"item_group": from_group})
    if cnt:
        frappe.db.sql(
            """UPDATE `tabItem` SET item_group=%s WHERE item_group=%s""",
            (misc_name, from_group),
        )
    return cnt


def _recursive_delete_item_group(name, misc_name, failed, audit_lines):
    if not frappe.db.exists("Item Group", name):
        return 0, 0
    if name in {ROOT, RAW, MISC, ADM, PROC, "Finished Goods"}:
        return 0, 0
    parent = frappe.db.get_value("Item Group", name, "parent_item_group")
    if parent == "Finished Goods":
        return 0, 0
    items_moved = 0
    deleted = 0
    children = frappe.get_all(
        "Item Group", filters={"parent_item_group": name}, pluck="name"
    )
    for child in children:
        cm, cd = _recursive_delete_item_group(child, misc_name, failed, audit_lines)
        items_moved += cm
        deleted += cd
    try:
        moved = _move_items_to_misc(name, misc_name)
        items_moved += moved or 0
        frappe.delete_doc("Item Group", name, ignore_permissions=True, force=True)
        deleted += 1
        audit_lines.append(f"Deleted Item Group '{name}', items moved to {misc_name}: {moved}")
    except Exception as e:
        failed.append(f"{name}: {str(e)}")
        frappe.log_error(frappe.get_traceback(), f"Item Group delete failed: {name}")
    return items_moved, deleted


def _migrate_tools_to_tool_instruments():
    """Rename Tools → Tool Instruments semantics: move items then remove Tools."""
    extra_created = 0
    if frappe.db.exists("Item Group", "Tools"):
        if _ensure_item_group("Tool Instruments", ROOT, 0):
            extra_created += 1
        frappe.db.sql(
            """UPDATE `tabItem` SET item_group=%s WHERE item_group=%s""",
            ("Tool Instruments", "Tools"),
        )
        try:
            frappe.delete_doc("Item Group", "Tools", ignore_permissions=True, force=True)
            frappe.logger().info("Deleted legacy Item Group: Tools")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Could not delete Tools Item Group")
    elif not frappe.db.exists("Item Group", "Tool Instruments"):
        if _ensure_item_group("Tool Instruments", ROOT, 0):
            extra_created += 1
    return extra_created


def execute():
    created = 0
    deleted = 0
    items_moved_total = 0
    failed = []
    audit_lines = []

    # --- B1 Preflight ---
    if not frappe.db.exists("Item Group", ROOT):
        frappe.throw(_("Missing root Item Group '{0}'").format(ROOT))

    created += 1 if _ensure_item_group(MISC, ROOT, 0) else 0
    created += 1 if _ensure_item_group(RAW, ROOT, 0) else 0

    # --- B2 Parents ---
    created += 1 if _ensure_item_group(ADM, ROOT, 1) else 0
    created += 1 if _ensure_item_group(PROC, ROOT, 1) else 0

    # --- B3 Leaves ---
    for nm in NEW_RAW_LEAVES:
        created += 1 if _ensure_item_group(nm, RAW, 0) else 0
    for nm in NEW_ADMIN_LEAVES:
        created += 1 if _ensure_item_group(nm, ADM, 0) else 0
    for nm in NEW_PROCESS_LEAVES:
        created += 1 if _ensure_item_group(nm, PROC, 0) else 0

    # --- B4 Standalone + Finished Goods ---
    created += _migrate_tools_to_tool_instruments()

    for nm in NEW_STANDALONE_LEAVES:
        created += 1 if _ensure_item_group(nm, ROOT, 0) else 0

    # Finished Goods subtree (preserve / seed minimal structure)
    created += 1 if _ensure_item_group("Finished Goods", ROOT, 1) else 0
    for ch in FINISHED_GOODS_CHILDREN:
        created += 1 if _ensure_item_group(ch, "Finished Goods", 0) else 0

    # --- B5 Cleanup under Raw Material ---
    canonical_raw = set(NEW_RAW_LEAVES)
    rm_children = frappe.get_all(
        "Item Group",
        filters={"parent_item_group": RAW},
        fields=["name", "is_group"],
    )
    for row in rm_children:
        nm = row.name
        if nm in canonical_raw:
            continue
        cm, cd = _recursive_delete_item_group(nm, MISC, failed, audit_lines)
        items_moved_total += cm
        deleted += cd

    # Cleanup explicit legacy leaf names that may exist outside Raw Material parent
    for legacy in LEGACY_PURGE_NAMES:
        if not frappe.db.exists("Item Group", legacy):
            continue
        is_g = frappe.db.get_value("Item Group", legacy, "is_group")
        parent = frappe.db.get_value("Item Group", legacy, "parent_item_group")
        if parent in ("Finished Goods",) or (
            parent and frappe.db.get_value("Item Group", parent, "parent_item_group") == "Finished Goods"
        ):
            continue
        if not is_g:
            cm, cd = _recursive_delete_item_group(legacy, MISC, failed, audit_lines)
            items_moved_total += cm
            deleted += cd

    frappe.db.commit()

    summary = (
        "Item Group restructure complete.\n"
        f"Created (approx new docs): {created}\n"
        f"Deleted Item Groups: {deleted}\n"
        f"Items reparented to Miscellaneous (row updates): {items_moved_total}\n"
        f"Failed deletions (manual review): {failed}"
    )
    frappe.log_error(summary, "PEPL Item Group Restructure v2")

    frappe.db.commit()
