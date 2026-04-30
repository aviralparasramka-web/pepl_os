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
        {"label": _("Submitted On"), "fieldname": "submission_date_display", "fieldtype": "Date", "width": 120},
        {"label": _("Days Pending"), "fieldname": "days_pending", "fieldtype": "Int", "width": 110},
        {"label": _("Items"), "fieldname": "items_count", "fieldtype": "Int", "width": 70},
        {"label": _("Bid Value"), "fieldname": "total_bid_value", "fieldtype": "Currency", "width": 140},
        {"label": _("Title"), "fieldname": "tender_title", "fieldtype": "Data", "width": 220},
    ]


def get_data(filters):
    conditions = ["status = 'Submitted'"]

    if filters.get("sector"):
        conditions.append("sector = %(sector)s")
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")

    where_clause = " AND ".join(conditions)

    tenders = frappe.db.sql(
        f"""
        SELECT
            t.name,
            t.nit_number,
            t.customer,
            t.sector,
            t.bid_submission_deadline as submission_date_display,
            t.tender_title,
            t.total_bid_value,
            (SELECT COUNT(*) FROM `tabPEPL Tender Item` WHERE parent = t.name) as items_count
        FROM `tabPEPL Tender` t
        WHERE {where_clause}
        ORDER BY t.bid_submission_deadline DESC
        """,
        filters,
        as_dict=True,
    )

    today_date = getdate(today())
    for row in tenders:
        if row.submission_date_display:
            sub_date = getdate(row.submission_date_display)
            row["days_pending"] = date_diff(today_date, sub_date)
        else:
            row["days_pending"] = None

    return tenders


def get_summary(data):
    if not data:
        return []

    total_value = sum((d.get("total_bid_value") or 0) for d in data)
    long_pending = sum(
        1 for d in data if d.get("days_pending") and d["days_pending"] > 30
    )

    return [
        {"value": len(data), "label": _("Awaiting Decision"), "datatype": "Int"},
        {"value": total_value, "label": _("Total Bid Value"), "datatype": "Currency"},
        {
            "value": long_pending,
            "label": _("Pending > 30 days"),
            "datatype": "Int",
            "indicator": "Orange" if long_pending > 0 else "Green",
        },
    ]
