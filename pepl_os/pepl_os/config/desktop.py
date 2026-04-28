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
                    "description": _("Government tender tracking — NIT, items, bid documents, outcome")
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
                },
                {
                    "type": "doctype",
                    "name": "PEPL Product Drawing",
                    "label": _("Product Drawings"),
                    "description": _("Assembly drawings with revisions and component nest")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Item Drawing",
                    "label": _("Item Drawings"),
                    "description": _("Component drawings with revision history")
                },
                {
                    "type": "doctype",
                    "name": "PEPL Specification",
                    "label": _("Specifications"),
                    "description": _("Performance, customer, RDSO/DQA specs")
                }
            ]
        }
    ]
