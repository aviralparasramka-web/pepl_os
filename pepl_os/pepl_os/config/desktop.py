from frappe import _


def get_data():
    return [
        {
            "module_name": "PEPL OS",
            "color": "#003580",
            "icon": "octicon octicon-tools",
            "type": "module",
            "label": _("PEPL OS"),
            "items": [
                {
                    "type": "doctype",
                    "name": "PEPL Tender",
                    "label": _("Tenders"),
                    "description": _("Government tender tracking")
                },
                {
                    "type": "doctype",
                    "name": "PEPL CST Cost Sheet",
                    "label": _("Cost Sheets"),
                    "description": _("Per-item costing with BOM, competitor history, financial tabulation")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Product Master",
                    "label": _("Product Master"),
                    "description": _("Unified product catalog")
                },
                {
                    "type": "doctype",
                    "name": "PEPL RM Group",
                    "label": _("RM Groups"),
                    "description": _("Raw material classification — synced to ERPNext Item Groups")
                },
                {
                    "type": "doctype",
                    "name": "Vendor Approval Status",
                    "label": _("Vendor Approval Status")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Company Document",
                    "label": _("Company Document Library")
                }
            ]
        }
    ]
