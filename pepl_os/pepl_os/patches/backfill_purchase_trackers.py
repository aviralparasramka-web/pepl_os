"""Create PEPL Purchase Tracker for submitted POs missing a tracker (idempotent)."""

import frappe

from pepl_os.pepl_os.doc_events.purchase_order_tracker import (
    create_purchase_tracker_on_submit,
)


def execute():
    po_names = frappe.get_all(
        "Purchase Order",
        filters={"docstatus": 1},
        pluck="name",
    )
    for name in po_names:
        if frappe.db.exists("PEPL Purchase Tracker", {"linked_purchase_order": name}):
            continue
        doc = frappe.get_doc("Purchase Order", name)
        create_purchase_tracker_on_submit(doc, None)
    frappe.db.commit()
