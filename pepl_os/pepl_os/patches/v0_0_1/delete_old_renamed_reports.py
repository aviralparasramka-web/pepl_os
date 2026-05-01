import frappe


def execute():
    """Delete old reports with parens/slashes that were renamed in v0.0.1.
    These reports cannot be deleted via UI because is_standard is locked.
    This patch runs once during migration and removes them properly.
    """

    old_reports = [
        "Tender Pipeline (Active)",
        "Tender Pipeline (Awaiting Outcome)",
        "Tender Win/Loss Analysis",
        "CST History (Per Item)",
    ]

    for report_name in old_reports:
        if frappe.db.exists("Report", report_name):
            try:
                frappe.db.set_value("Report", report_name, "is_standard", "No")
                frappe.db.commit()

                frappe.delete_doc("Report", report_name, ignore_permissions=True, force=True)
                frappe.db.commit()

                print(f"Deleted old report: {report_name}")
            except Exception as e:
                print(f"Could not delete {report_name}: {str(e)}")
        else:
            print(f"Report not found (already deleted?): {report_name}")
