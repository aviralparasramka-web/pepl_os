# Copyright (c) 2026, PEPL and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns():
    return [
        {"label": _("Tender No"), "fieldname": "name", "fieldtype": "Link", "options": "PEPL Tender", "width": 130},
        {"label": _("NIT Number"), "fieldname": "nit_number", "fieldtype": "Data", "width": 140},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Sector"), "fieldname": "sector", "fieldtype": "Data", "width": 100},
        {"label": _("Sub-Sector"), "fieldname": "sub_sector", "fieldtype": "Data", "width": 130},
        {"label": _("Deadline"), "fieldname": "bid_submission_deadline", "fieldtype": "Datetime", "width": 140},
        {"label": _("Days Left"), "fieldname": "days_remaining", "fieldtype": "Int", "width": 90},
        {"label": _("Items"), "fieldname": "items_count", "fieldtype": "Int", "width": 70},
        {"label": _("Est. Value"), "fieldname": "total_estimated_value", "fieldtype": "Currency", "width": 130},
        {"label": _("Title"), "fieldname": "tender_title", "fieldtype": "Data", "width": 220},
    ]


def get_data(filters):
    conditions = ["status = 'Active Bid'"]

    if filters.get("sector"):
        conditions.append("sector = %(sector)s")
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
    if filters.get("from_date"):
        conditions.append("bid_submission_deadline >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("bid_submission_deadline <= %(to_date)s")

    where_clause = " AND ".join(conditions)

    tenders = frappe.db.sql(
        f"""
        SELECT
            t.name,
            t.nit_number,
            t.customer,
            t.sector,
            t.sub_sector,
            t.bid_submission_deadline,
            t.tender_title,
            t.total_estimated_value,
            (SELECT COUNT(*) FROM `tabPEPL Tender Item` WHERE parent = t.name) as items_count
        FROM `tabPEPL Tender` t
        WHERE {where_clause}
        ORDER BY t.bid_submission_deadline ASC
        """,
        filters,
        as_dict=True,
    )

    today_date = getdate(today())
    for row in tenders:
        if row.bid_submission_deadline:
            deadline_date = getdate(row.bid_submission_deadline)
            row["days_remaining"] = date_diff(deadline_date, today_date)
        else:
            row["days_remaining"] = None

    return tenders


def get_summary(data):
    if not data:
        return []

    total_value = sum((d.get("total_estimated_value") or 0) for d in data)
    urgent_count = sum(
        1 for d in data
        if d.get("days_remaining") is not None and d["days_remaining"] <= 3
    )

    return [
        {"value": len(data), "label": _("Active Tenders"), "datatype": "Int"},
        {"value": total_value, "label": _("Total Pipeline Value"), "datatype": "Currency"},
        {
            "value": urgent_count,
            "label": _("Deadline \u2264 3 days"),
            "datatype": "Int",
            "indicator": "Red" if urgent_count > 0 else "Green",
        },
    ]
