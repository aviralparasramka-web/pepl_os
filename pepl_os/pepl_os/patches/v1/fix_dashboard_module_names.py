import frappe


def execute():
    """One-shot: update dashboard records from old module
    name 'Parasramka ERPNext' to 'PEPL OS'."""
    old_module = "Parasramka ERPNext"
    new_module = "PEPL OS"

    affected_doctypes = [
        "Workspace",
        "Number Card",
        "Dashboard Chart",
        "Report",
    ]

    total_updated = 0
    for doctype in affected_doctypes:
        try:
            count_before = frappe.db.count(
                doctype, {"module": old_module}
            )
            if count_before > 0:
                frappe.db.sql(f"""
                    UPDATE `tab{doctype}`
                    SET module = %s
                    WHERE module = %s
                """, (new_module, old_module))
                total_updated += count_before
                print(
                    f"  Updated {count_before} "
                    f"{doctype} records"
                )
        except Exception as e:
            print(f"  Skipped {doctype}: {e}")

    frappe.db.commit()
    frappe.clear_cache()
    print(
        f"fix_dashboard_module_names: {total_updated} "
        f"total records updated"
    )
