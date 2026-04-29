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

scheduler_events = {}

doc_events = {}

doctype_js = {}

page_js = {}