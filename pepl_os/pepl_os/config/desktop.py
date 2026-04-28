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
                },
                {
                    "type": "doctype",
                    "name": "PEPL Product Drawing",
                    "label": _("Product Drawings"),
                    "description": _("Assembly drawings with component nest")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Item Drawing",
                    "label": _("Item Drawings"),
                    "description": _("Component-level drawings")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Specification",
                    "label": _("Specifications"),
                    "description": _("Performance specs, customer specs, RDSO/DQA specs — many-to-many with Items")
                }
            ]
        }
    ]
