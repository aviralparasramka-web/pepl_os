# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe
from frappe import _
from frappe.utils import add_days, flt, today


def create_mr_draft_from_so(doc, method=None):
    """When a Sales Order is submitted, walk each product item's default
    BOM and auto-create a Material Request DRAFT for any RM components
    with a shortfall (current stock + on-order + open-MR < required).

    Registered as Sales Order.on_submit in hooks.py (chained AFTER the
    existing sales_order_module5 handler).

    Errors are logged but do NOT block SO submission.
    """
    try:
        if not frappe.db.has_column("Item", "is_product"):
            frappe.log_error(
                f"MR auto-draft skipped for SO {doc.name}: 'is_product' "
                f"custom field missing on Item DocType. Suvadip's custom "
                f"field deployment may be pending.",
                "MR Auto-Draft Skipped"
            )
            return

        shortfalls = _aggregate_shortfalls(doc)
        if not shortfalls:
            return

        mr = _build_mr_draft(doc, shortfalls)
        if not mr or not mr.items:
            return

        mr.insert(ignore_permissions=True)
        frappe.msgprint(_(
            "Material Request {0} drafted with {1} component(s) for "
            "Sales Order {2}. Review in Purchase before submission."
        ).format(mr.name, len(mr.items), doc.name))
    except Exception as e:
        frappe.log_error(
            f"MR auto-draft failed for SO {doc.name}: {str(e)}",
            "MR Auto-Draft from SO"
        )


def _aggregate_shortfalls(so):
    """Walk each SO product item's BOM, calculate component requirements,
    aggregate by item_code, then subtract stock + on-order + open-MR.
    Returns dict: {item_code: {qty, uom}} for items with shortfall > 0."""
    aggregated = {}

    for so_item in (so.items or []):
        is_product = frappe.db.get_value("Item", so_item.item_code, "is_product") or 0
        if not is_product:
            # Bought-out items being resold — they are themselves the shortfall
            _add_to_aggregate(aggregated, so_item.item_code, flt(so_item.qty), so_item.uom)
            continue

        bom_name = frappe.db.get_value(
            "BOM",
            {"item": so_item.item_code, "is_default": 1, "is_active": 1, "docstatus": 1},
            "name"
        )
        if not bom_name:
            frappe.log_error(
                f"No active default BOM for product {so_item.item_code} (SO {so.name}). "
                f"MR auto-draft skipped for this line.",
                "MR Auto-Draft Warning"
            )
            continue

        bom = frappe.get_doc("BOM", bom_name)
        bom_qty = flt(bom.quantity) or 1
        scale = flt(so_item.qty) / bom_qty

        for bom_row in (bom.items or []):
            # Skip non-stock items (services, etc.)
            is_stock = frappe.db.get_value("Item", bom_row.item_code, "is_stock_item") or 0
            if not is_stock:
                continue
            # Skip nested products (Production module will handle multi-level explosion later)
            is_sub_product = frappe.db.get_value("Item", bom_row.item_code, "is_product") or 0
            if is_sub_product:
                continue

            required = flt(bom_row.qty) * scale
            _add_to_aggregate(aggregated, bom_row.item_code, required, bom_row.uom)

    # Subtract supply (stock + on-order + open-MR)
    shortfalls = {}
    for item_code, data in aggregated.items():
        in_stock = _get_stock_position(item_code)
        on_order = _get_on_order_position(item_code)
        open_mr = _get_open_mr_position(item_code)
        net_supply = in_stock + on_order + open_mr
        shortfall = data["qty"] - net_supply
        if shortfall > 0:
            shortfalls[item_code] = {"qty": shortfall, "uom": data["uom"]}

    return shortfalls


def _add_to_aggregate(agg, item_code, qty, uom):
    if item_code in agg:
        agg[item_code]["qty"] += qty
    else:
        agg[item_code] = {"qty": qty, "uom": uom}


def _build_mr_draft(so, shortfalls):
    """Build a Material Request DRAFT (not submitted) for the shortfall items."""
    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Purchase"
    mr.transaction_date = today()
    mr.schedule_date = so.delivery_date or add_days(today(), 14)
    mr.company = so.company

    # Custom fields from Day 5
    mr.mr_source = "SO BOM Auto-Draft"
    mr.linked_so = so.name
    mr.priority = "Routine"
    mr.auto_drafted = 1

    for item_code, data in shortfalls.items():
        mr.append("items", {
            "item_code": item_code,
            "qty": data["qty"],
            "uom": data["uom"],
            "schedule_date": so.delivery_date or add_days(today(), 14),
        })

    return mr


# ─────────────────────────────────────────────
# Supply position helpers (also used by inventory_intelligence API)
# ─────────────────────────────────────────────

def _get_stock_position(item_code):
    result = frappe.db.sql(
        "SELECT COALESCE(SUM(actual_qty), 0) FROM `tabBin` WHERE item_code = %s",
        (item_code,)
    )
    return flt(result[0][0]) if result else 0


def _get_on_order_position(item_code):
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(poi.qty - poi.received_qty), 0)
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.item_code = %s AND po.docstatus = 1
        AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
    """, (item_code,))
    return flt(result[0][0]) if result else 0


def _get_open_mr_position(item_code):
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(mri.qty - mri.ordered_qty), 0)
        FROM `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mri.item_code = %s AND mr.docstatus = 1
        AND mr.status NOT IN ('Issued', 'Stopped', 'Cancelled')
    """, (item_code,))
    return flt(result[0][0]) if result else 0
