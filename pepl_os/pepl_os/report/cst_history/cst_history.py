import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}

    if not filters.get("item"):
        frappe.msgprint(_("Please select an Item to see its CST history"))
        return get_columns(), [], None, None, []

    columns = get_columns()
    data = get_data(filters)
    return columns, data, None, None, get_summary(data)


def get_columns():
    return [
        {"label": _("Tender No"), "fieldname": "tender_name", "fieldtype": "Link", "options": "PEPL Tender", "width": 130},
        {"label": _("NIT Number"), "fieldname": "nit_number", "fieldtype": "Data", "width": 130},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 160},
        {"label": _("Sector"), "fieldname": "sector", "fieldtype": "Data", "width": 90},
        {"label": _("Tender Date"), "fieldname": "tender_date", "fieldtype": "Date", "width": 110},
        {"label": _("Quantity"), "fieldname": "quantity", "fieldtype": "Float", "width": 80},
        {"label": _("Our Price"), "fieldname": "our_price", "fieldtype": "Currency", "width": 110},
        {"label": _("Our Rank"), "fieldname": "our_rank", "fieldtype": "Data", "width": 80},
        {"label": _("L1 Competitor"), "fieldname": "l1_competitor", "fieldtype": "Data", "width": 140},
        {"label": _("L1 Price"), "fieldname": "l1_price", "fieldtype": "Currency", "width": 110},
        {"label": _("L2 Competitor"), "fieldname": "l2_competitor", "fieldtype": "Data", "width": 140},
        {"label": _("L2 Price"), "fieldname": "l2_price", "fieldtype": "Currency", "width": 110},
        {"label": _("Outcome"), "fieldname": "outcome", "fieldtype": "Data", "width": 90},
    ]


def get_data(filters):
    item = filters.get("item")

    conditions = ["ti.item = %s"]
    params = [item]

    if filters.get("from_date"):
        conditions.append("t.bid_submission_deadline >= %s")
        params.append(filters["from_date"])
    if filters.get("to_date"):
        conditions.append("t.bid_submission_deadline <= %s")
        params.append(filters["to_date"])
    if filters.get("customer"):
        conditions.append("t.customer = %s")
        params.append(filters["customer"])
    if filters.get("sector"):
        conditions.append("t.sector = %s")
        params.append(filters["sector"])

    where_clause = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            t.name as tender_name,
            t.nit_number,
            t.customer,
            t.sector,
            t.bid_submission_deadline as tender_date,
            ti.name as ti_name,
            ti.quantity,
            ti.our_bid_unit_price as our_price,
            ti.our_rank,
            ti.outcome
        FROM `tabPEPL Tender Item` ti
        INNER JOIN `tabPEPL Tender` t ON ti.parent = t.name
        WHERE {where_clause}
        ORDER BY t.bid_submission_deadline DESC
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        competitors = frappe.db.sql(
            """
            SELECT competitor_name, competitor_price, rank
            FROM `tabPEPL Tender Item Competitor`
            WHERE parent = %s
            ORDER BY
                CASE rank
                    WHEN 'L1' THEN 1 WHEN 'L2' THEN 2 WHEN 'L3' THEN 3
                    WHEN 'L4' THEN 4 WHEN 'L5' THEN 5 ELSE 99
                END
            LIMIT 2
            """,
            row.ti_name,
            as_dict=True,
        )

        if len(competitors) >= 1:
            row["l1_competitor"] = competitors[0].competitor_name
            row["l1_price"] = competitors[0].competitor_price
        if len(competitors) >= 2:
            row["l2_competitor"] = competitors[1].competitor_name
            row["l2_price"] = competitors[1].competitor_price

    return rows


def get_summary(data):
    if not data:
        return []

    won_count = sum(1 for d in data if d.get("outcome") == "Won")
    avg_our_price = (
        sum((d.get("our_price") or 0) for d in data) / len(data) if data else 0
    )

    return [
        {"value": len(data), "label": _("Total Tenders"), "datatype": "Int"},
        {"value": won_count, "label": _("Won"), "datatype": "Int", "indicator": "Green"},
        {"value": avg_our_price, "label": _("Avg Our Price"), "datatype": "Currency"},
    ]
