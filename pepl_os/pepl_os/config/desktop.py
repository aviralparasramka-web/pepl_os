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
                {"type": "doctype", "name": "PEPL Tender", "label": _("Tenders")},
                {"type": "doctype", "name": "PEPL CST Cost Sheet", "label": _("Cost Sheets")},
                {"type": "doctype", "name": "PEPL Product Master", "label": _("Product Master")},
                {"type": "doctype", "name": "PEPL RM Group", "label": _("RM Groups")},
                {"type": "doctype", "name": "Vendor Approval Status", "label": _("Vendor Approval Status")},
                {"type": "doctype", "name": "PEPL Company Document", "label": _("Company Documents")},
                {"type": "report", "name": "Tender Pipeline Active", "doctype": "PEPL Tender", "is_query_report": 1},
                {"type": "report", "name": "Tender Pipeline Awaiting Outcome", "doctype": "PEPL Tender", "is_query_report": 1},
                {"type": "report", "name": "Tender Win Loss Analysis", "doctype": "PEPL Tender", "is_query_report": 1},
                {"type": "report", "name": "CST History", "doctype": "PEPL Tender", "is_query_report": 1},
                {"type": "report", "name": "Vendor Approval Register", "doctype": "Vendor Approval Status", "is_query_report": 1},
                {"type": "report", "name": "Competitor Analysis", "doctype": "PEPL Tender", "is_query_report": 1},
                {"type": "report", "name": "Monthly Sales Pipeline", "doctype": "PEPL Tender", "is_query_report": 1},
            ],
        }
    ]
