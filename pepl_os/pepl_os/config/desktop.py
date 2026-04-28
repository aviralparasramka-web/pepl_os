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
                    "name": "Vendor Approval Status",
                    "label": _("Vendor Approval Status"),
                    "description": _("Per-item vendor approval tracking — Railways and Defence stages")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Company Document",
                    "label": _("Company Document Library"),
                    "description": _("Master library — GST, Udyam, ISO, etc. with version history")
                }
            ]
        }
    ]
