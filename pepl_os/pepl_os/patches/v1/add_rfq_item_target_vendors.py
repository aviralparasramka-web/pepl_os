"""
Patch: Add target_vendors Table MultiSelect field on Request for Quotation Item.

Idempotent — create_custom_fields with update=True.
Requires PEPL RFQ Item Target Vendor DocType to be synced first (post_model_sync).
"""

import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    # Defensive: install the linked child DocType from
    # disk if it doesn't exist yet. Required because this
    # patch adds a Table MultiSelect custom field that
    # references "PEPL RFQ Item Target Vendor", and
    # Frappe validates the link target by looking it up
    # in tabDocType.
    target_doctype = "PEPL RFQ Item Target Vendor"
    if not frappe.db.exists("DocType", target_doctype):
        try:
            from frappe.modules.import_file import import_file_by_path
            json_path = frappe.get_app_path(
                "pepl_os",
                "doctype",
                "pepl_rfq_item_target_vendor",
                "pepl_rfq_item_target_vendor.json",
            )
            if os.path.exists(json_path):
                import_file_by_path(json_path, force=True)
                frappe.db.commit()
            else:
                frappe.log_error(
                    f"DocType JSON not found at: {json_path}",
                    "add_rfq_item_target_vendors",
                )
        except Exception as e:
            frappe.log_error(
                f"import_file_by_path failed: {e}",
                "add_rfq_item_target_vendors",
            )

    # Sanity check before proceeding
    if not frappe.db.exists("DocType", target_doctype):
        frappe.throw(
            f"Cannot proceed: DocType {target_doctype} could "
            f"not be installed. Check log for details."
        )

    # Existing patch logic continues unchanged below
    frappe.reload_doctype("Request for Quotation Item", force=True)

    custom_fields = {
        "Request for Quotation Item": [
            {
                "fieldname": "target_vendors",
                "label": "Target Vendors",
                "fieldtype": "Table MultiSelect",
                "options": "PEPL RFQ Item Target Vendor",
                "insert_after": "description",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
