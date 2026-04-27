# PEPL Operating System — Custom Frappe App (pepl_os)

## Company Context
- Company: Parasramka Engineering Pvt. Ltd. (PEPL)
- Sector: Heavy Engineering — Defence and Railways
- ERP: ERPNext v16 on Frappe Cloud
- App name: pepl_os
- GitHub: https://github.com/aviralparasramka-web/pepl_os
- Inner package: pepl_os/pepl_os/

Note: The old parasramka_erpnext app was deprecated
because of a Frappe Cloud cache issue that could not
be resolved. The new pepl_os app contains the same
business logic under a clean fresh deployment.

## Business Context
- Engineer-to-Order (ETO) manufacturer
- Customers: Railway zones (Loco/Coaches/Zonal),
  Defence (MIL/YIL/AWEIL/Private)
- Modules to build (in this order):
  1. Vendor Approval Status — per-item approval state machine
  2. Tender Management — NIT tracking with auto-fetched approval state
  3. CST Cost Sheet — BOM costing with competitor analysis
  4. NPD Project — new item development (Stage-Gate 0 to 5)
  5. PSD Tracker — Performance Security Deposit lifecycle
  6. Production Lot — defence/railway lot tracking
  7. Dispatch and Payment Tracker — replaces CO7 Tracker,
     handles both Railways (R-Note/CO7) and Defence
     (I-Note/IC) in one DocType
  8. Print Formats (8 letters)
  9. Reports (9 reports)
  10. Claude AI Integration + PEPL Assistant
  11. Raven and WhatsApp notification layer

## Technical Rules — ALWAYS Follow
- DocTypes go in:
  pepl_os/pepl_os/doctype/
- Every DocType needs exactly 4 files:
  doctype_name.json
  doctype_name.py
  doctype_name.js
  __init__.py
- Module name in all JSON files: "PEPL OS"
- All currency fields: INR
- Naming series formats:
  TND-.YYYY.- (Tender)
  CST-.YYYY.- (Cost Sheet)
  PSD-.YYYY.- (PSD Tracker)
  NPD-.YYYY.- (NPD Project)
  LOT-.YYYY.- (Production Lot)
- Always use frappe.utils for date functions
- Always use frappe.get_all() not raw SQL
- track_changes: 1 on all DocTypes
- Never hardcode values — use frappe.db.get_value
- pyproject.toml: flit_core build backend ONLY
- __init__.py: __version__ defined for flit dynamic version
- Module name: "PEPL OS" (not "PEPL_OS" — display name with space)
- Python package: pepl_os (lowercase, underscore)
- modules.txt: contains exactly one line: PEPL OS

## Deployment
- Cursor writes files and pushes to GitHub
- Frappe Cloud auto-pulls from GitHub on deploy
- No SSH access to Frappe Cloud
