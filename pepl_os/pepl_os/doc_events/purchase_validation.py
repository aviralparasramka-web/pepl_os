# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe
from frappe import _


SUSPENSION_BLOCK_PO = ["Temporary Suspended", "Permanent Suspended"]
SUSPENSION_BLOCK_PR_PI = ["Permanent Suspended"]


def _get_supplier_status(supplier_name):
    """Return the approval_status of the linked PEPL Supplier Approval,
    or None if no approval record exists."""
    if not supplier_name:
        return None
    return frappe.db.get_value(
        "PEPL Supplier Approval",
        {"linked_supplier": supplier_name},
        "approval_status"
    )


def block_po_if_suspended(doc, method=None):
    """Block Purchase Order submit if vendor is Temp or Perm Suspended.
    Registered as Purchase Order.before_submit in hooks.py."""
    status = _get_supplier_status(doc.supplier)
    if status in SUSPENSION_BLOCK_PO:
        frappe.throw(_(
            "Cannot submit this Purchase Order. Supplier '{0}' is in status "
            "'{1}'. Reach out to Purchase Manager to resolve before placing "
            "new POs."
        ).format(doc.supplier, status))


def block_pr_if_perm_suspended(doc, method=None):
    """Block Purchase Receipt submit if vendor is Permanently Suspended.
    Also enforce heat_number for RM-category items.
    Registered as Purchase Receipt.before_submit in hooks.py."""
    status = _get_supplier_status(doc.supplier)
    if status in SUSPENSION_BLOCK_PR_PI:
        frappe.throw(_(
            "Cannot submit this Purchase Receipt. Supplier '{0}' is "
            "Permanently Suspended. All transactions are blocked."
        ).format(doc.supplier))

    # Enforce heat_number for RM receipts
    has_rm_item = any(
        frappe.db.get_value("Item", item.item_code, "item_category") == "Raw Material"
        for item in (doc.items or [])
    )
    if has_rm_item and not doc.get("heat_number"):
        frappe.throw(_(
            "Heat Number is mandatory for Purchase Receipts containing "
            "Raw Material items. Please enter the heat/melt number from "
            "the supplier's test certificate."
        ))


def block_pi_if_perm_suspended(doc, method=None):
    """Block Purchase Invoice submit if vendor is Permanently Suspended.
    Registered as Purchase Invoice.before_submit in hooks.py."""
    status = _get_supplier_status(doc.supplier)
    if status in SUSPENSION_BLOCK_PR_PI:
        frappe.throw(_(
            "Cannot submit this Purchase Invoice. Supplier '{0}' is "
            "Permanently Suspended. All transactions are blocked."
        ).format(doc.supplier))
