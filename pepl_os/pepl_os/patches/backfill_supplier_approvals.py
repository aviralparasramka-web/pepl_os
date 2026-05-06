"""
Patch: Create one PEPL Supplier Approval record per existing Supplier
that doesn't already have one. Status defaults to Pending.
Idempotent — safe to run multiple times.
"""

import frappe


def execute():
    suppliers = frappe.get_all("Supplier", pluck="name")
    created = 0
    skipped = 0

    for supplier_name in suppliers:
        # Skip if approval record already exists
        if frappe.db.exists("PEPL Supplier Approval", {"linked_supplier": supplier_name}):
            skipped += 1
            continue

        try:
            doc = frappe.new_doc("PEPL Supplier Approval")
            doc.linked_supplier = supplier_name
            doc.approval_status = "Pending"
            doc.insert(ignore_permissions=True)
            created += 1
        except Exception as e:
            frappe.log_error(
                f"Failed to backfill approval for Supplier {supplier_name}: {str(e)}",
                "Supplier Approval Backfill"
            )

    frappe.db.commit()
    print(f"Supplier Approval backfill: created {created}, skipped {skipped}")
