"""
Procurement Funnel — Script Report
Returns 6 funnel stages with aggregated INR values.
Each row: { stage, count, value_inr }
"""

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "stage",
            "label": "Stage",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "count",
            "label": "Count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "fieldname": "value_inr",
            "label": "Value (INR)",
            "fieldtype": "Currency",
            "width": 160,
        },
    ]


def get_data(filters):
    # --- 1. Material Requests (open / in progress) ---
    mr = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(total), 0) AS val
        FROM `tabMaterial Request`
        WHERE docstatus = 1
          AND status NOT IN ('Stopped', 'Cancelled')
        """,
        as_dict=True,
    )[0]

    # --- 2. RFQs (submitted) ---
    rfq = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, 0 AS val
        FROM `tabRequest for Quotation`
        WHERE docstatus = 1
        """,
        as_dict=True,
    )[0]

    # --- 3. Purchase Orders (submitted) ---
    po = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(grand_total), 0) AS val
        FROM `tabPurchase Order`
        WHERE docstatus = 1
        """,
        as_dict=True,
    )[0]

    # --- 4. Purchase Receipts (submitted) ---
    pr = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(grand_total), 0) AS val
        FROM `tabPurchase Receipt`
        WHERE docstatus = 1
        """,
        as_dict=True,
    )[0]

    # --- 5. Purchase Invoices (submitted) ---
    inv = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(grand_total), 0) AS val
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
        """,
        as_dict=True,
    )[0]

    # --- 6. Paid (invoices with zero outstanding) ---
    paid = frappe.db.sql(
        """
        SELECT COUNT(*) AS cnt, COALESCE(SUM(grand_total), 0) AS val
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND outstanding_amount = 0
        """,
        as_dict=True,
    )[0]

    return [
        {"stage": "Material Request", "count": mr["cnt"], "value_inr": mr["val"]},
        {"stage": "RFQ",              "count": rfq["cnt"], "value_inr": rfq["val"]},
        {"stage": "Purchase Order",   "count": po["cnt"],  "value_inr": po["val"]},
        {"stage": "Purchase Receipt", "count": pr["cnt"],  "value_inr": pr["val"]},
        {"stage": "Invoice",          "count": inv["cnt"], "value_inr": inv["val"]},
        {"stage": "Paid",             "count": paid["cnt"],"value_inr": paid["val"]},
    ]
