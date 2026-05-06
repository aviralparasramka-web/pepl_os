# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import json
import frappe
from frappe.utils import flt

# Reuse the supply position helpers from sales_order_mr_draft to avoid duplication
from pepl_os.pepl_os.doc_events.sales_order_mr_draft import (
    _get_stock_position,
    _get_on_order_position,
    _get_open_mr_position,
)


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
            "in_stock": _get_stock_position(code),
            "on_order": _get_on_order_position(code),
            "open_mr": _get_open_mr_position(code),
        }
    return result
