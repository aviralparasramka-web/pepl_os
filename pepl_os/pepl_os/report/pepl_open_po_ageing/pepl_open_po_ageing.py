"""Open PO ageing joined with PEPL Purchase Tracker."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("PO Number"), "fieldname": "po", "fieldtype": "Link", "options": "Purchase Order", "width": 140},
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
        {"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 100},
        {"label": _("Days Outstanding"), "fieldname": "days_outstanding", "fieldtype": "Int", "width": 120},
        {"label": _("Ageing Bucket"), "fieldname": "ageing_bucket", "fieldtype": "Data", "width": 130},
        {"label": _("PO Amount"), "fieldname": "po_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("Tracker Status"), "fieldname": "tracker_status", "fieldtype": "Data", "width": 140},
        {"label": _("Expected Delivery"), "fieldname": "expected_delivery_date", "fieldtype": "Date", "width": 120},
        {"label": _("Colour"), "fieldname": "colour_flag", "fieldtype": "Data", "width": 90},
    ]


def _as_list(val):
    if val is None or val == "":
        return []
    return list(val) if isinstance(val, (list, tuple)) else [val]


def get_data(filters):
    conditions = ["po.docstatus = 1", "IFNULL(po.status,'') NOT IN ('Closed','Cancelled','Completed')"]
    params = {}

    if filters.get("from_date"):
        conditions.append("po.transaction_date >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("po.transaction_date <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    suppliers = _as_list(filters.get("supplier"))
    if suppliers:
        conditions.append("po.supplier IN %(suppliers)s")
        params["suppliers"] = tuple(suppliers)

    where_sql = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT po.name AS po,
               po.supplier AS supplier,
               po.transaction_date AS po_date,
               po.grand_total AS po_amount,
               pt.current_status AS tracker_status,
               pt.ageing_bucket AS tracker_ageing_bucket,
               pt.days_outstanding AS tracker_days_outstanding,
               pt.expected_delivery_date AS expected_delivery_date
        FROM `tabPurchase Order` po
        LEFT JOIN `tabPEPL Purchase Tracker` pt ON pt.linked_purchase_order = po.name
        WHERE {where_sql}
        ORDER BY COALESCE(pt.days_outstanding, DATEDIFF(CURDATE(), po.transaction_date)) DESC
        """,
        params,
        as_dict=True,
    )

    out = []
    for r in rows:
        days = r.tracker_days_outstanding
        if days is None:
            days = date_diff(getdate(today()), r.po_date) if r.po_date else 0
        bucket = r.tracker_ageing_bucket or _bucket_from_days(days)
        colour = _colour_from_days(days)
        row_out = {
            "po": r.po,
            "supplier": r.supplier,
            "po_date": r.po_date,
            "days_outstanding": days,
            "ageing_bucket": bucket,
            "po_amount": r.po_amount,
            "tracker_status": r.tracker_status or "—",
            "expected_delivery_date": r.expected_delivery_date,
            "colour_flag": colour,
        }
        status_pick = _as_list(filters.get("current_status"))
        if status_pick and row_out["tracker_status"] not in status_pick:
            continue
        bucket_pick = _as_list(filters.get("ageing_bucket"))
        if bucket_pick and row_out["ageing_bucket"] not in bucket_pick:
            continue
        out.append(row_out)
    return out


def _bucket_from_days(days):
    d = int(days or 0)
    if d <= 7:
        return "0-7 days"
    if d <= 15:
        return "8-15 days"
    if d <= 30:
        return "16-30 days"
    return "30+ days"


def _colour_from_days(days):
    d = int(days or 0)
    if d <= 7:
        return "green"
    if d <= 15:
        return "yellow"
    if d <= 30:
        return "orange"
    return "red"
