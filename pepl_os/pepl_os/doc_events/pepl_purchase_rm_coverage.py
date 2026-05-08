# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


def update_rm_coverage_last_supply(doc, method=None):
    """After PO submit, stamp last_supply_date on matching RM Coverage rows."""
    if not doc.supplier:
        return
    sa_name = frappe.db.get_value(
        "PEPL Supplier Approval", {"linked_supplier": doc.supplier}, "name"
    )
    if not sa_name:
        return

    rm_dates = {}
    for row in doc.items or []:
        if not row.item_code:
            continue
        ig = frappe.db.get_value("Item", row.item_code, "item_group")
        if not ig:
            continue
        rm = frappe.db.get_value("PEPL RM Group", {"linked_item_group": ig}, "name")
        if not rm:
            continue
        prev = rm_dates.get(rm)
        td = doc.transaction_date
        if not prev or str(td) > str(prev):
            rm_dates[rm] = td

    if not rm_dates:
        return

    sa = frappe.get_doc("PEPL Supplier Approval", sa_name)
    changed = False
    for cov in sa.rm_coverage:
        if cov.rm_group in rm_dates:
            cov.last_supply_date = rm_dates[cov.rm_group]
            changed = True
    if changed:
        sa.flags.ignore_permissions = True
        sa.save()
