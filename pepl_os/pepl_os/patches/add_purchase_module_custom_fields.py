"""
Patch: Add Purchase Module custom fields on Supplier, Material Request,
Purchase Order, Purchase Receipt (Day 5 Purchase MVP).
Idempotent — uses create_custom_fields with update=True.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Supplier": [
            {
                "fieldname": "pepl_approval_status",
                "label": "PEPL Approval Status",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "supplier_name",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": (
                    "Auto-synced from PEPL Supplier Approval. "
                    "Updated whenever the linked approval record is saved."
                ),
            },
        ],
        "Material Request": [
            {
                "fieldname": "mr_source",
                "label": "MR Source",
                "fieldtype": "Select",
                "options": "\nSO BOM Auto-Draft\nShop Floor Request\nReorder Level\nCapex\nOther",
                "insert_after": "material_request_type",
                "description": "Origin of this Material Request.",
            },
            {
                "fieldname": "linked_so",
                "label": "Linked Sales Order",
                "fieldtype": "Link",
                "options": "Sales Order",
                "insert_after": "mr_source",
            },
            {
                "fieldname": "priority",
                "label": "Priority",
                "fieldtype": "Select",
                "options": "Routine\nUrgent\nCritical",
                "default": "Routine",
                "insert_after": "linked_so",
            },
            {
                "fieldname": "auto_drafted",
                "label": "Auto-Drafted by System",
                "fieldtype": "Check",
                "read_only": 1,
                "insert_after": "priority",
                "description": "Set by the SO submit hook when MR was auto-generated.",
            },
        ],
        "Purchase Order": [
            {
                "fieldname": "linked_so",
                "label": "Linked Sales Order",
                "fieldtype": "Link",
                "options": "Sales Order",
                "insert_after": "schedule_date",
            },
            {
                "fieldname": "linked_mr",
                "label": "Linked Material Request",
                "fieldtype": "Link",
                "options": "Material Request",
                "insert_after": "linked_so",
            },
            {
                "fieldname": "priority",
                "label": "Priority",
                "fieldtype": "Select",
                "options": "Routine\nUrgent\nCritical",
                "default": "Routine",
                "insert_after": "linked_mr",
            },
            {
                "fieldname": "is_rate_contract",
                "label": "Is Rate Contract",
                "fieldtype": "Check",
                "insert_after": "priority",
                "description": "Tick if this PO is a standing rate contract with drawdowns.",
            },
            {
                "fieldname": "contract_start_date",
                "label": "Contract Start Date",
                "fieldtype": "Date",
                "depends_on": "eval:doc.is_rate_contract",
                "insert_after": "is_rate_contract",
            },
            {
                "fieldname": "contract_end_date",
                "label": "Contract End Date",
                "fieldtype": "Date",
                "depends_on": "eval:doc.is_rate_contract",
                "insert_after": "contract_start_date",
            },
            {
                "fieldname": "contract_quantity",
                "label": "Contracted Quantity",
                "fieldtype": "Float",
                "depends_on": "eval:doc.is_rate_contract",
                "insert_after": "contract_end_date",
            },
            {
                "fieldname": "quantity_drawn",
                "label": "Quantity Drawn",
                "fieldtype": "Float",
                "read_only": 1,
                "depends_on": "eval:doc.is_rate_contract",
                "insert_after": "contract_quantity",
                "description": "Auto-calculated from receipts against this contract.",
            },
            {
                "fieldname": "is_job_work",
                "label": "Is Job Work",
                "fieldtype": "Check",
                "insert_after": "quantity_drawn",
            },
            {
                "fieldname": "is_csm_related",
                "label": "CSM Related",
                "fieldtype": "Check",
                "insert_after": "is_job_work",
                "description": "Tick if this PO involves customer-supplied material.",
            },
            {
                "fieldname": "linked_grn",
                "label": "Linked GRN (for Service POs)",
                "fieldtype": "Link",
                "options": "Purchase Receipt",
                "insert_after": "is_csm_related",
                "description": (
                    "For service POs (TPI, Heat Treatment, Plating, etc.), "
                    "link to the parent GRN. Quantity will be validated against GRN."
                ),
            },
            {
                "fieldname": "is_capex",
                "label": "Is Capex",
                "fieldtype": "Check",
                "insert_after": "linked_grn",
                "description": "Tick for capital expenditure. Above ₹2L requires MD approval.",
            },
        ],
        "Purchase Receipt": [
            {
                "fieldname": "heat_number",
                "label": "Heat Number",
                "fieldtype": "Data",
                "insert_after": "supplier_delivery_note",
                "description": (
                    "Foundry heat/melt number for traceability. "
                    "Mandatory for RM receipts (enforced via validation)."
                ),
            },
            {
                "fieldname": "supplier_test_certificate",
                "label": "Supplier Test Certificate",
                "fieldtype": "Attach",
                "insert_after": "heat_number",
            },
            {
                "fieldname": "visual_inspection_pass",
                "label": "Visual Inspection Pass",
                "fieldtype": "Check",
                "insert_after": "supplier_test_certificate",
            },
            {
                "fieldname": "dimensional_inspection_pass",
                "label": "Dimensional Inspection Pass",
                "fieldtype": "Check",
                "insert_after": "visual_inspection_pass",
            },
            {
                "fieldname": "discrepancy_flag",
                "label": "Discrepancy Detected",
                "fieldtype": "Check",
                "insert_after": "dimensional_inspection_pass",
            },
            {
                "fieldname": "debit_note_required",
                "label": "Debit Note Required",
                "fieldtype": "Check",
                "depends_on": "eval:doc.discrepancy_flag",
                "insert_after": "discrepancy_flag",
            },
        ],
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
