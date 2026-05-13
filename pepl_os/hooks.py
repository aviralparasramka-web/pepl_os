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
        "dt": "Custom Field",
        "filters": [
            ["dt", "=", "Request for Quotation Item"],
            ["fieldname", "=", "target_vendors"]
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
        "pepl_os.pepl_os.doctype.pepl_purchase_tracker.pepl_purchase_tracker.update_all_purchase_trackers_daily",
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
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_po_if_suspended",
        "on_submit": [
            "pepl_os.pepl_os.doc_events.purchase_order_tracker.create_purchase_tracker_on_submit",
            "pepl_os.pepl_os.doc_events.pepl_purchase_rm_coverage.update_rm_coverage_last_supply",
        ],
    },
    "Purchase Receipt": {
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_pr_if_perm_suspended",
        "on_submit": "pepl_os.pepl_os.doc_events.purchase_receipt_tracker.update_purchase_tracker_on_pr_submit",
    },
    "Purchase Invoice": {
        "before_submit": "pepl_os.pepl_os.doc_events.purchase_validation.block_pi_if_perm_suspended"
    },
    "Request for Quotation": {
        "on_submit": [
            "pepl_os.pepl_os.doc_events.request_for_quotation_pepl.log_non_approved_rfq_suppliers",
            "pepl_os.pepl_os.api.quotation_comparison.auto_create_on_rfq_submit",
        ],
    },
    "Supplier Quotation": {
        "on_submit": "pepl_os.pepl_os.api.quotation_comparison.auto_refresh_on_sq_submit",
    },
}

doctype_js = {
    "Material Request": "public/js/material_request_dashboard.js",
    "PEPL Tender": "public/js/tender_bid_readiness.js",
    "Sales Order": "public/js/sales_order_product_readiness.js",
    "PEPL CST Cost Sheet": "public/js/cst_cost_sheet_intelligence.js",
    "Request for Quotation": [
        "public/js/request_for_quotation_pepl.js",
        "public/js/request_for_quotation_phase2.js",
    ],
}

page_js = {}

override_doctype_class = {
    "Request for Quotation": "pepl_os.pepl_os.overrides.request_for_quotation.PeplRequestForQuotation",
}
