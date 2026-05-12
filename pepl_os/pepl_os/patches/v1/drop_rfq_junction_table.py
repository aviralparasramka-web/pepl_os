"""
Patch: Drop junction DocType table and stale custom fields from Phase 2 v1.

Removes:
  - DB table: tabPEPL RFQ Item Vendor Selection
  - Custom fields on Request for Quotation: per_item_vendor_selections_section,
    per_item_vendor_selections

All operations are defensive — missing objects are silently skipped.
"""

import frappe


def execute():
    # Defensive prefix per V4 closing rule.
    # Reload the old junction DocType (may or may not exist depending on
    # prior deploy state). Wrapped in try/except so a missing DocType
    # definition on disk does not abort the patch.
    try:
        frappe.reload_doctype("PEPL RFQ Item Vendor Selection", force=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"reload_doctype failed: {e}",
            "drop_rfq_junction_table",
        )

    # Drop the junction table if it still exists
    try:
        if frappe.db.table_exists("tabPEPL RFQ Item Vendor Selection"):
            frappe.db.sql("DROP TABLE `tabPEPL RFQ Item Vendor Selection`")
            frappe.log_error(
                "tabPEPL RFQ Item Vendor Selection dropped by migration patch",
                "RFQ Phase 2 refactor",
            )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "drop_rfq_junction_table: table drop skipped")

    # Remove the old section-break custom field on the parent RFQ
    for fieldname in ("per_item_vendor_selections_section", "per_item_vendor_selections"):
        try:
            if frappe.db.exists(
                "Custom Field",
                {"dt": "Request for Quotation", "fieldname": fieldname},
            ):
                frappe.db.delete(
                    "Custom Field",
                    {"dt": "Request for Quotation", "fieldname": fieldname},
                )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"drop_rfq_junction_table: custom field {fieldname} drop skipped",
            )

    frappe.db.commit()
