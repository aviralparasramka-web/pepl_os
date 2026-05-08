"""Backfill PEPL Supplier Approval.rm_coverage from PO history (18 months)."""

import frappe
from frappe.utils import add_months, getdate, today


def execute():
    lookback_months = 18
    cutoff = add_months(getdate(today()), -lookback_months)

    rows_created = 0
    suppliers_touched = 0
    suppliers_no_po = []

    sa_names = frappe.get_all("PEPL Supplier Approval", pluck="name")

    for sa_name in sa_names:
        sa = frappe.get_doc("PEPL Supplier Approval", sa_name)
        supplier = sa.linked_supplier
        if not supplier:
            continue

        groups = frappe.db.sql(
            """
            SELECT DISTINCT i.item_group AS item_group,
                   MIN(po.transaction_date) AS first_po
            FROM `tabPurchase Order Item` poi
            INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
            INNER JOIN `tabItem` i ON i.name = poi.item_code
            WHERE po.supplier = %s
              AND po.docstatus = 1
              AND po.transaction_date >= %s
              AND IFNULL(i.item_group, '') != ''
            GROUP BY i.item_group
            """,
            (supplier, cutoff),
            as_dict=True,
        )

        if not groups:
            suppliers_no_po.append(supplier)
            continue

        existing_rm = {r.rm_group for r in sa.rm_coverage}
        changed = False

        for g in groups:
            ig = g.item_group
            rm = frappe.db.get_value("PEPL RM Group", {"linked_item_group": ig}, "name")
            if not rm or rm in existing_rm:
                continue
            sa.append(
                "rm_coverage",
                {
                    "rm_group": rm,
                    "since_date": g.first_po or today(),
                    "rate_card_attached": 0,
                    "notes": "Auto-backfilled from PO history",
                },
            )
            existing_rm.add(rm)
            rows_created += 1
            changed = True

        if changed:
            sa.flags.ignore_permissions = True
            sa.save()
            suppliers_touched += 1

    frappe.log_error(
        "Backfilled rm_coverage from PO history.\n"
        f"Suppliers updated: {suppliers_touched}\n"
        f"Coverage rows created: {rows_created}\n"
        f"Suppliers with no PO history in window: {suppliers_no_po[:200]}",
        "PEPL RM Coverage Backfill",
    )
    frappe.db.commit()
