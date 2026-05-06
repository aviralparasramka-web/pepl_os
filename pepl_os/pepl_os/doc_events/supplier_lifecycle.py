# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe


def on_supplier_insert(doc, method=None):
    """When a new Supplier is created, auto-create a corresponding
    PEPL Supplier Approval record in Pending state.
    Registered in hooks.py as Supplier.after_insert.
    """
    if frappe.db.exists("PEPL Supplier Approval", {"linked_supplier": doc.name}):
        return

    approval = frappe.new_doc("PEPL Supplier Approval")
    approval.linked_supplier = doc.name
    approval.approval_status = "Pending"
    approval.insert(ignore_permissions=True)
    frappe.db.commit()
