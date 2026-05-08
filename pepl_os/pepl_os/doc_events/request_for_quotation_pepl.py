# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


def log_non_approved_rfq_suppliers(doc, method=None):
    """On RFQ submit: log suppliers that are not in Approved PEPL Supplier Approval state."""
    user = frappe.session.user
    for row in doc.suppliers or []:
        sup = row.supplier
        if not sup:
            continue
        status = frappe.db.get_value(
            "PEPL Supplier Approval", {"linked_supplier": sup}, "approval_status"
        )
        if status == "Approved":
            continue
        sa_name = frappe.db.get_value(
            "PEPL Supplier Approval", {"linked_supplier": sup}, "name"
        )
        reason = (
            f"RFQ {doc.name}: supplier {sup} added without Approved status "
            f"(status={status or 'no PEPL Supplier Approval'})"
        )
        if sa_name:
            sa = frappe.get_doc("PEPL Supplier Approval", sa_name)
            sa.append(
                "override_log",
                {
                    "override_user": user,
                    "rfq_reference": doc.name,
                    "override_reason": reason[:240],
                },
            )
            sa.flags.ignore_permissions = True
            sa.save()
        else:
            frappe.log_error(reason, "RFQ supplier override (no approval record)")
