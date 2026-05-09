"""Rename Report docs so report_name matches pepl_* report folder slugs (fixes ModuleNotFoundError)."""

import frappe

_RENAMES = (
    ("Open PO Ageing", "PEPL Open PO Ageing"),
    ("Outstanding Vendor Bills", "PEPL Outstanding Vendor Bills"),
    ("MSME 45-Day Compliance", "PEPL MSME 45-Day Compliance"),
    ("Vendor RM Coverage", "PEPL Vendor RM Coverage"),
)


def execute():
    for old_name, new_name in _RENAMES:
        if not frappe.db.exists("Report", old_name):
            continue
        if frappe.db.exists("Report", new_name):
            continue
        try:
            frappe.rename_doc(
                "Report",
                old_name,
                new_name,
                force=True,
                ignore_permissions=True,
            )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"rename_pepl_reports: {old_name} -> {new_name}",
            )
    frappe.db.commit()
