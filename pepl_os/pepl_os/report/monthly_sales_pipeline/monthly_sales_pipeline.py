import frappe
from frappe import _
from frappe.utils import today


def execute(filters=None):
    filters = filters or {}
    year = filters.get("year") or today()[:4]

    columns = get_columns()
    data = get_data(year, filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 110},
        {"label": _("Total Tenders"), "fieldname": "total_tenders", "fieldtype": "Int", "width": 110},
        {"label": _("Estimated Value"), "fieldname": "total_estimated", "fieldtype": "Currency", "width": 140},
        {"label": _("Bid Value"), "fieldname": "total_bid", "fieldtype": "Currency", "width": 140},
        {"label": _("Won Value"), "fieldname": "won_value", "fieldtype": "Currency", "width": 140},
        {"label": _("Lost Value"), "fieldname": "lost_value", "fieldtype": "Currency", "width": 140},
        {"label": _("Pending Value"), "fieldname": "pending_value", "fieldtype": "Currency", "width": 140},
        {"label": _("Win Rate %"), "fieldname": "win_rate", "fieldtype": "Percent", "width": 100},
    ]


def get_data(year, filters):
    sector_filter = ""
    params = [year]

    if filters.get("sector"):
        sector_filter = "AND sector = %s"
        params.append(filters["sector"])

    rows = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(bid_submission_deadline, '%%Y-%%m') as month_key,
            DATE_FORMAT(bid_submission_deadline, '%%b %%Y') as month,
            COUNT(*) as total_tenders,
            SUM(total_estimated_value) as total_estimated,
            SUM(total_bid_value) as total_bid,
            SUM(CASE WHEN status = 'Won' THEN total_bid_value ELSE 0 END) as won_value,
            SUM(CASE WHEN status = 'Lost' THEN total_bid_value ELSE 0 END) as lost_value,
            SUM(CASE WHEN status IN ('Active Bid', 'Submitted') THEN total_bid_value ELSE 0 END) as pending_value,
            SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END) as won_count,
            SUM(CASE WHEN status = 'Lost' THEN 1 ELSE 0 END) as lost_count
        FROM `tabPEPL Tender`
        WHERE YEAR(bid_submission_deadline) = %s {sector_filter}
        GROUP BY month_key
        ORDER BY month_key ASC
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        decided = (row.get("won_count") or 0) + (row.get("lost_count") or 0)
        row["win_rate"] = ((row.get("won_count") or 0) / decided * 100) if decided > 0 else 0

    return rows


def get_chart(data):
    if not data:
        return None

    return {
        "data": {
            "labels": [d.get("month") for d in data],
            "datasets": [
                {"name": "Estimated", "values": [d.get("total_estimated") or 0 for d in data]},
                {"name": "Bid", "values": [d.get("total_bid") or 0 for d in data]},
                {"name": "Won", "values": [d.get("won_value") or 0 for d in data]},
            ],
        },
        "type": "line",
        "colors": ["#666666", "#003580", "#28a745"],
    }


def get_summary(data):
    if not data:
        return []

    total_estimated = sum((d.get("total_estimated") or 0) for d in data)
    total_won = sum((d.get("won_value") or 0) for d in data)
    total_pending = sum((d.get("pending_value") or 0) for d in data)

    return [
        {"value": total_estimated, "label": _("YTD Estimated"), "datatype": "Currency"},
        {"value": total_won, "label": _("YTD Won"), "datatype": "Currency", "indicator": "Green"},
        {"value": total_pending, "label": _("In Pipeline"), "datatype": "Currency", "indicator": "Orange"},
    ]
