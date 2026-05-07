# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import json

import frappe
from frappe.utils import flt


def get_stock_position(item_code):
    result = frappe.db.sql(
        "SELECT COALESCE(SUM(actual_qty), 0) FROM `tabBin` WHERE item_code = %s",
        (item_code,),
    )
    return flt(result[0][0]) if result else 0


def get_on_order_position(item_code):
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(poi.qty - poi.received_qty), 0)
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.item_code = %s AND po.docstatus = 1
        AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
    """,
        (item_code,),
    )
    return flt(result[0][0]) if result else 0


def get_open_mr_position(item_code):
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(mri.qty - mri.ordered_qty), 0)
        FROM `tabMaterial Request Item` mri
        INNER JOIN `tabMaterial Request` mr ON mr.name = mri.parent
        WHERE mri.item_code = %s AND mr.docstatus = 1
        AND mr.status NOT IN ('Issued', 'Stopped', 'Cancelled')
    """,
        (item_code,),
    )
    return flt(result[0][0]) if result else 0


@frappe.whitelist()
def get_items_supply_position(item_codes):
    """Return supply-side position for a batch of items.
    Used by the Material Request dashboard panel.

    Args:
        item_codes: JSON-encoded list of item codes (passed as string from JS)

    Returns:
        dict: {item_code: {in_stock, on_order, open_mr}}
    """
    if isinstance(item_codes, str):
        item_codes = json.loads(item_codes)

    result = {}
    for code in item_codes:
        if not code:
            continue
        result[code] = {
            "in_stock": get_stock_position(code),
            "on_order": get_on_order_position(code),
            "open_mr": get_open_mr_position(code),
        }
    return result
