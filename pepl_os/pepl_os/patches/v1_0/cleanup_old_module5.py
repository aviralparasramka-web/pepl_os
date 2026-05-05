import frappe


def execute():
    """Cleanup old Module 5 DocTypes and tables.
    Safe to run multiple times — checks existence before drop.
    """

    old_doctypes = [
        "PEPL PSD Tracker",
        "PEPL PSD Submission",
        "PEPL SO Document",
        "PEPL SO Document Attachment",
    ]

    for dt in old_doctypes:
        table_name = f"tab{dt}"
        try:
            frappe.db.sql(f"DROP TABLE IF EXISTS `{table_name}`")
            print(f"Dropped table: {table_name}")
        except Exception as e:
            print(f"Could not drop {table_name}: {str(e)}")

        if frappe.db.exists("DocType", dt):
            try:
                frappe.delete_doc("DocType", dt, force=True)
                print(f"Removed DocType definition: {dt}")
            except Exception as e:
                print(f"Could not remove DocType {dt}: {str(e)}")

    frappe.db.commit()
    print("Module 5 cleanup complete")
