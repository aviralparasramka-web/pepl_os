# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


def create_purchase_tracker_on_submit(doc, method=None):
    """Auto-create PEPL Purchase Tracker when a Purchase Order is submitted."""
    try:
        if frappe.db.exists(
            "PEPL Purchase Tracker", {"linked_purchase_order": doc.name}
        ):
            return

        tracker = frappe.new_doc("PEPL Purchase Tracker")
        tracker.linked_purchase_order = doc.name

        so_names = []
        mr_names = []
        for item in doc.items or []:
            so = getattr(item, "sales_order", None)
            if so:
                so_names.append(so)
            mr = getattr(item, "material_request", None)
            if mr:
                mr_names.append(mr)

        if so_names:
            tracker.linked_so = so_names[0]
        if mr_names:
            tracker.linked_mr = mr_names[0]

        tracker.flags.ignore_permissions = True
        tracker.insert()
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Purchase Tracker auto-create failed for PO {doc.name}",
        )
