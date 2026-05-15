# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd.
import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link",
         "options": "Warehouse", "width": 140},
        {"label": "Rack", "fieldname": "rack_number", "fieldtype": "Data", "width": 80},
        {"label": "Bin", "fieldname": "bin_number", "fieldtype": "Data", "width": 80},
        {"label": "Shelf", "fieldname": "shelf_position", "fieldtype": "Data", "width": 70},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link",
         "options": "Item", "width": 160},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Qty", "fieldname": "qty_received", "fieldtype": "Float", "width": 100},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Link",
         "options": "UOM", "width": 70},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link",
         "options": "Supplier", "width": 140},
        {"label": "QC", "fieldname": "qc_status", "fieldtype": "Data", "width": 90},
        {"label": "Docs", "fieldname": "documents_status", "fieldtype": "Data", "width": 110},
        {"label": "GRN", "fieldname": "linked_purchase_receipt", "fieldtype": "Link",
         "options": "Purchase Receipt", "width": 130},
        {"label": "Receipt Log", "fieldname": "name", "fieldtype": "Link",
         "options": "PEPL Receipt Log", "width": 130},
    ]

    conditions = []
    if filters.get("warehouse"):
        conditions.append("warehouse = %(warehouse)s")
    if filters.get("rack_number"):
        conditions.append("rack_number LIKE %(rack_number)s")
    if filters.get("bin_number"):
        conditions.append("bin_number LIKE %(bin_number)s")
    if filters.get("item_code"):
        conditions.append("item_code = %(item_code)s")
    if filters.get("qc_status"):
        conditions.append("qc_status = %(qc_status)s")

    if filters.get("rack_number"):
        filters["rack_number"] = "%" + filters["rack_number"] + "%"
    if filters.get("bin_number"):
        filters["bin_number"] = "%" + filters["bin_number"] + "%"

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    data = frappe.db.sql(
        f"""
        SELECT
            name, warehouse, rack_number, bin_number, shelf_position,
            item_code, item_name, qty_received, uom, supplier,
            qc_status, documents_status, linked_purchase_receipt
        FROM `tabPEPL Receipt Log`
        {where}
        ORDER BY warehouse, rack_number, bin_number, item_code
        """,
        filters,
        as_dict=True,
    )

    return columns, data
