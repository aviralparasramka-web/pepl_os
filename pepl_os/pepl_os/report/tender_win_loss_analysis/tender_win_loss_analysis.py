import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": _("Tender No"), "fieldname": "name", "fieldtype": "Link", "options": "PEPL Tender", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": _("Sector"), "fieldname": "sector", "fieldtype": "Data", "width": 100},
        {"label": _("Decision Date"), "fieldname": "decision_date", "fieldtype": "Date", "width": 120},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
        {"label": _("Items Total"), "fieldname": "items_total", "fieldtype": "Int", "width": 90},
        {"label": _("Items Won"), "fieldname": "items_won", "fieldtype": "Int", "width": 90},
        {"label": _("Items Lost"), "fieldname": "items_lost", "fieldtype": "Int", "width": 90},
        {"label": _("Win Rate %"), "fieldname": "win_rate", "fieldtype": "Percent", "width": 100},
        {"label": _("Bid Value"), "fieldname": "total_bid_value", "fieldtype": "Currency", "width": 130},
        {"label": _("Loss Reason"), "fieldname": "loss_reason", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    conditions = ["status IN ('Won', 'Lost', 'Partially Won')"]

    if filters.get("from_date"):
        conditions.append("decision_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("decision_date <= %(to_date)s")
    if filters.get("sector"):
        conditions.append("sector = %(sector)s")
    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
    if filters.get("status"):
        conditions = [c for c in conditions if "status IN" not in c]
        conditions.append("status = %(status)s")
    if filters.get("loss_reason"):
        conditions.append("loss_reason = %(loss_reason)s")

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            name, customer, sector, decision_date, status,
            (SELECT COUNT(*) FROM `tabPEPL Tender Item`
             WHERE parent = `tabPEPL Tender`.name) as items_total,
            items_won, items_lost, win_rate, total_bid_value, loss_reason
        FROM `tabPEPL Tender`
        WHERE {where_clause}
        ORDER BY decision_date DESC
        """,
        filters,
        as_dict=True,
    )


def get_chart(data):
    if not data:
        return None

    won = sum(1 for d in data if d.get("status") == "Won")
    lost = sum(1 for d in data if d.get("status") == "Lost")
    partial = sum(1 for d in data if d.get("status") == "Partially Won")

    return {
        "data": {
            "labels": ["Won", "Lost", "Partially Won"],
            "datasets": [{"values": [won, lost, partial]}],
        },
        "type": "donut",
        "colors": ["#28a745", "#dc3545", "#ffc107"],
    }


def get_summary(data):
    if not data:
        return []

    won = sum(1 for d in data if d.get("status") == "Won")
    lost = sum(1 for d in data if d.get("status") == "Lost")
    partial = sum(1 for d in data if d.get("status") == "Partially Won")
    total_decided = won + lost + partial
    overall_win_rate = (won / total_decided * 100) if total_decided > 0 else 0
    won_value = sum(
        (d.get("total_bid_value") or 0) for d in data if d.get("status") == "Won"
    )

    return [
        {"value": len(data), "label": _("Total Tenders"), "datatype": "Int"},
        {"value": won, "label": _("Won"), "datatype": "Int", "indicator": "Green"},
        {"value": lost, "label": _("Lost"), "datatype": "Int", "indicator": "Red"},
        {"value": overall_win_rate, "label": _("Win Rate"), "datatype": "Percent"},
        {"value": won_value, "label": _("Value Won"), "datatype": "Currency"},
    ]
