import frappe
from frappe import _
from frappe.utils import getdate, today, date_diff


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns():
    return [
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": _("Drawing No"), "fieldname": "drawing_no", "fieldtype": "Data", "width": 140},
        {"label": _("Sector"), "fieldname": "sector", "fieldtype": "Data", "width": 110},
        {"label": _("Sub-Sector"), "fieldname": "sub_sector", "fieldtype": "Data", "width": 130},
        {"label": _("Stage"), "fieldname": "current_stage", "fieldtype": "Data", "width": 170},
        {"label": _("Status"), "fieldname": "approval_status", "fieldtype": "Data", "width": 130},
        {"label": _("Last Updated"), "fieldname": "modified", "fieldtype": "Date", "width": 120},
        {"label": _("Days in Stage"), "fieldname": "days_in_stage", "fieldtype": "Int", "width": 120},
    ]


def get_data(filters):
    conditions = ["1=1"]

    if filters.get("sector"):
        conditions.append("vas.sector = %(sector)s")
    if filters.get("item"):
        conditions.append("vas.item = %(item)s")

    where_clause = " AND ".join(conditions)

    records = frappe.db.sql(
        f"""
        SELECT
            vas.name,
            vas.item,
            vas.sector,
            vas.railways_stage,
            vas.defence_stage,
            vas.modified,
            i.custom_drawing_no as drawing_no
        FROM `tabVendor Approval Status` vas
        LEFT JOIN `tabItem` i ON i.name = vas.item
        WHERE {where_clause}
        ORDER BY vas.modified DESC
        """,
        filters,
        as_dict=True,
    )

    today_date = getdate(today())
    filter_status = filters.get("status")
    filtered_records = []

    for row in records:
        if row.sector == "Railways":
            stage = row.railways_stage or "Unapproved"
            row["sub_sector"] = "Railways"
        elif row.sector == "Defence":
            stage = row.defence_stage or "Source Development"
            row["sub_sector"] = "Defence"
        else:
            stage = "Unknown"
            row["sub_sector"] = row.sector or "Unknown"

        row["current_stage"] = stage

        if stage in ["Approved", "Established"]:
            row["approval_status"] = "Approved"
        elif stage in ["Developmental", "Source Development"]:
            row["approval_status"] = "In Progress"
        elif stage == "Unapproved":
            row["approval_status"] = "Unapproved"
        else:
            row["approval_status"] = "Unknown"

        if row.modified:
            row["days_in_stage"] = date_diff(today_date, getdate(row.modified))

        if filter_status and filter_status != "All":
            if row["approval_status"] != filter_status:
                continue

        filtered_records.append(row)

    return filtered_records


def get_summary(data):
    if not data:
        return []

    approved = sum(1 for d in data if d.get("approval_status") == "Approved")
    in_progress = sum(1 for d in data if d.get("approval_status") == "In Progress")
    unapproved = sum(1 for d in data if d.get("approval_status") == "Unapproved")
    approval_pct = (approved / len(data) * 100) if data else 0

    return [
        {"value": len(data), "label": _("Total Items"), "datatype": "Int"},
        {"value": approved, "label": _("Approved"), "datatype": "Int", "indicator": "Green"},
        {"value": in_progress, "label": _("In Progress"), "datatype": "Int", "indicator": "Orange"},
        {"value": unapproved, "label": _("Unapproved"), "datatype": "Int", "indicator": "Red"},
        {"value": approval_pct, "label": _("Approval %"), "datatype": "Percent"},
    ]
