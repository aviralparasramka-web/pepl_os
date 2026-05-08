# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


@frappe.whitelist()
def supplier_list_query_for_rfq(doctype, txt, searchfield, start, page_len, filters):
    """Link query — surfaces Approved PEPL Supplier Approval vendors first."""
    start = int(start)
    page_len = int(page_len)
    txt = (txt or "").strip()
    if txt:
        cond = "(s.name LIKE %(txt)s OR s.supplier_name LIKE %(txt)s)"
        args = {"txt": f"%{txt}%"}
    else:
        cond = "1=1"
        args = {}
    return frappe.db.sql(
        f"""
        SELECT s.name, s.supplier_name
        FROM `tabSupplier` s
        INNER JOIN `tabPEPL Supplier Approval` sa
            ON sa.linked_supplier = s.name AND sa.approval_status = 'Approved'
        WHERE {cond}
        ORDER BY s.supplier_name
        LIMIT %(start)s, %(page_len)s
        """,
        dict(args, start=start, page_len=page_len),
    )
