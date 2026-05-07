# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


def update_purchase_tracker_on_pr_submit(doc, method=None):
    """Link Purchase Receipt to PEPL Purchase Tracker by PO."""
    try:
        po_seen = set()
        for item in doc.items or []:
            po = getattr(item, "purchase_order", None)
            if not po or po in po_seen:
                continue
            po_seen.add(po)

            tracker_name = frappe.db.get_value(
                "PEPL Purchase Tracker",
                {"linked_purchase_order": po},
                "name",
            )
            if not tracker_name:
                continue

            tracker = frappe.get_doc("PEPL Purchase Tracker", tracker_name)
            if not tracker.grn_reference:
                tracker.grn_reference = doc.name
                tracker.flags.ignore_permissions = True
                tracker.save()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Purchase Tracker GRN link failed for PR {getattr(doc, 'name', '')}",
        )
