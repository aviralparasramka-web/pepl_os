app_name = "pepl_os"
app_title = "PEPL OS"
app_publisher = "Parasramka Engineering Pvt. Ltd."
app_description = "PEPL Operating System - AI-powered ERP for Defence and Railways engineering"
app_email = "aviral.parasramka@gmail.com"
app_license = "MIT"
app_version = "0.0.1"

# These sections are intentionally empty.
# They will be filled module by module as we build.

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "PEPL OS"]
        ]
    },
    {
        "dt": "Role",
        "filters": [
            ["role_name", "in", ["Engineering Manager", "Engineering User", "Purchase User"]]
        ]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [
            ["role", "in", ["Engineering Manager", "Engineering User", "Purchase User"]]
        ]
    },
    "PEPL RM Group"
]

scheduler_events = {
    "daily": [
        "pepl_os.pepl_os.doctype.pepl_supplier_approval.pepl_supplier_approval.update_all_supplier_approvals_daily",
    ],
}

doc_events = {
    "Sales Order": {
        "on_submit": [
            "pepl_os.pepl_os.doc_events.sales_order_module5.on_submit",
            "pepl_os.pepl_os.doc_events.sales_order_mr_draft.create_mr_draft_from_so",
        ]
    },
    "Sales Invoice": {
        "on_submit": "pepl_os.pepl_os.doc_events.sales_invoice_module8.on_submit"
    },
    "Supplier": {
        "after_insert": "pepl_os.pepl_os.doc_events.supplier_lifecycle.on_supplier_insert"
    },
    "Purchase Order": {
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_po_if_suspended"
    },
    "Purchase Receipt": {
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_pr_if_perm_suspended"
    },
    "Purchase Invoice": {
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_pi_if_perm_suspended"
    },
}

doctype_js = {
    "Material Request": "public/js/material_request_dashboard.js",
}

page_js = {}
