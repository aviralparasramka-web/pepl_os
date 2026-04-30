import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data, filters)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": _("Tender No"), "fieldname": "tender_name", "fieldtype": "Link", "options": "PEPL Tender", "width": 130},
        {"label": _("NIT Number"), "fieldname": "nit_number", "fieldtype": "Data", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Sector"), "fieldname": "sector", "fieldtype": "Data", "width": 90},
        {"label": _("Tender Date"), "fieldname": "tender_date", "fieldtype": "Date", "width": 110},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": _("Competitor"), "fieldname": "competitor_name", "fieldtype": "Data", "width": 180},
        {"label": _("Their Price"), "fieldname": "competitor_price", "fieldtype": "Currency", "width": 110},
        {"label": _("Their Rank"), "fieldname": "rank", "fieldtype": "Data", "width": 90},
        {"label": _("Our Price"), "fieldname": "our_price", "fieldtype": "Currency", "width": 110},
        {"label": _("Our Rank"), "fieldname": "our_rank", "fieldtype": "Data", "width": 90},
        {"label": _("Outcome"), "fieldname": "outcome", "fieldtype": "Data", "width": 90},
        {"label": _("MSME"), "fieldname": "is_msme", "fieldtype": "Check", "width": 70},
    ]


def get_data(filters):
    conditions = ["1=1"]
    params = {}

    if filters.get("competitor_name"):
        conditions.append("tic.competitor_name LIKE %(competitor_name)s")
        params["competitor_name"] = f"%{filters['competitor_name']}%"
    if filters.get("from_date"):
        conditions.append("t.bid_submission_deadline >= %(from_date)s")
        params["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions.append("t.bid_submission_deadline <= %(to_date)s")
        params["to_date"] = filters["to_date"]
    if filters.get("sector"):
        conditions.append("t.sector = %(sector)s")
        params["sector"] = filters["sector"]
    if filters.get("outcome"):
        conditions.append("ti.outcome = %(outcome)s")
        params["outcome"] = filters["outcome"]

    where_clause = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            t.name as tender_name,
            t.nit_number,
            t.customer,
            t.sector,
            t.bid_submission_deadline as tender_date,
            ti.item,
            tic.competitor_name,
            tic.competitor_price,
            tic.rank,
            ti.our_bid_unit_price as our_price,
            ti.our_rank,
            ti.outcome,
            tic.is_msme
        FROM `tabPEPL Tender Item Competitor` tic
        INNER JOIN `tabPEPL Tender Item` ti ON tic.parent = ti.name
        INNER JOIN `tabPEPL Tender` t ON ti.parent = t.name
        WHERE {where_clause}
        ORDER BY t.bid_submission_deadline DESC
        """,
        params,
        as_dict=True,
    )


def get_chart(data):
    if not data:
        return None

    competitor_count = {}
    for row in data:
        name = row.get("competitor_name", "Unknown")
        competitor_count[name] = competitor_count.get(name, 0) + 1

    sorted_competitors = sorted(
        competitor_count.items(), key=lambda x: x[1], reverse=True
    )[:5]

    if not sorted_competitors:
        return None

    return {
        "data": {
            "labels": [c[0] for c in sorted_competitors],
            "datasets": [{"name": "Times Encountered", "values": [c[1] for c in sorted_competitors]}],
        },
        "type": "bar",
        "colors": ["#003580"],
    }


def get_summary(data, filters):
    if not data:
        return []

    summary = [{"value": len(data), "label": _("Total Encounters"), "datatype": "Int"}]

    if filters.get("competitor_name"):
        won_against = sum(1 for d in data if d.get("outcome") == "Won")
        lost_to = sum(1 for d in data if d.get("outcome") == "Lost")
        win_rate = (
            (won_against / (won_against + lost_to) * 100)
            if (won_against + lost_to) > 0
            else 0
        )
        summary.extend([
            {"value": won_against, "label": _("We Won"), "datatype": "Int", "indicator": "Green"},
            {"value": lost_to, "label": _("We Lost"), "datatype": "Int", "indicator": "Red"},
            {"value": win_rate, "label": _("Our Win Rate"), "datatype": "Percent"},
        ])

    return summary
