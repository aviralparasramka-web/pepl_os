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
                    "description": _("Government tender tracking with line items and bid documents")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Product Master",
                    "label": _("Product Master"),
                    "description": _("Unified product catalog — drawings, specs, assembly components, BOM")
                },
                {
                    "type": "doctype",
                    "name": "Vendor Approval Status",
                    "label": _("Vendor Approval Status"),
                    "description": _("Per-item vendor approval tracking")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Company Document",
                    "label": _("Company Document Library"),
                    "description": _("Master library — GST, Udyam, ISO with version history")
                }
            ]
        }
    ]
