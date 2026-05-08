"""Vendor ↔ RM coverage matrix (Supplier Approval.rm_coverage)."""

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    view_raw = (filters.get("view_as") or "Vendor").strip()
    view_alias = {"Vendor": "Vendor", "RM Group": "RM", "Coverage Gaps": "Gaps"}
    filters["_view"] = view_alias.get(view_raw, view_raw if view_raw in ("Vendor", "RM", "Gaps") else "Vendor")
    columns = get_columns(filters["_view"])
    data = get_data(filters, filters["_view"])
    return columns, data


def get_columns(view):
    base = [
        {"label": _("View"), "fieldname": "view_as", "fieldtype": "Data", "width": 90},
    ]
    if view == "Vendor":
        base.extend(
            [
                {"label": _("Supplier Approval"), "fieldname": "approval", "fieldtype": "Link", "options": "PEPL Supplier Approval", "width": 160},
                {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
                {"label": _("Approval Status"), "fieldname": "approval_status", "fieldtype": "Data", "width": 140},
                {"label": _("RM Group"), "fieldname": "rm_group", "fieldtype": "Link", "options": "PEPL RM Group", "width": 160},
                {"label": _("Specific Items"), "fieldname": "specific_items", "fieldtype": "Small Text", "width": 220},
                {"label": _("Since Date"), "fieldname": "since_date", "fieldtype": "Date", "width": 100},
                {"label": _("Last Supply Date"), "fieldname": "last_supply_date", "fieldtype": "Date", "width": 120},
            ]
        )
    elif view == "RM":
        base.extend(
            [
                {"label": _("RM Group"), "fieldname": "rm_group", "fieldtype": "Link", "options": "PEPL RM Group", "width": 160},
                {"label": _("Supplier Count"), "fieldname": "supplier_count", "fieldtype": "Int", "width": 110},
                {"label": _("Suppliers"), "fieldname": "supplier_names", "fieldtype": "Small Text", "width": 320},
            ]
        )
    else:
        base.extend(
            [
                {"label": _("RM Group (GAP)"), "fieldname": "rm_group", "fieldtype": "Link", "options": "PEPL RM Group", "width": 200},
                {"label": _("Issue"), "fieldname": "note", "fieldtype": "Data", "width": 260},
            ]
        )
    return base


def get_data(filters, view):
    if view == "Vendor":
        rows = []
        for sa_name in frappe.get_all("PEPL Supplier Approval", pluck="name"):
            doc = frappe.get_doc("PEPL Supplier Approval", sa_name)
            if filters.get("approval_status") and doc.approval_status != filters["approval_status"]:
                continue
            if filters.get("supplier") and doc.linked_supplier != filters["supplier"]:
                continue
            for cov in doc.rm_coverage or []:
                if filters.get("rm_group") and cov.rm_group != filters["rm_group"]:
                    continue
                specific = getattr(cov, "specific_items", None)
                rows.append(
                    {
                        "view_as": "Vendor",
                        "approval": doc.name,
                        "supplier": doc.linked_supplier,
                        "approval_status": doc.approval_status,
                        "rm_group": cov.rm_group,
                        "specific_items": str(specific or ""),
                        "since_date": cov.since_date,
                        "last_supply_date": cov.last_supply_date,
                    }
                )
        return rows

    if view == "RM":
        rm_map = {}
        for sa_name in frappe.get_all("PEPL Supplier Approval", pluck="name"):
            doc = frappe.get_doc("PEPL Supplier Approval", sa_name)
            if filters.get("approval_status") and doc.approval_status != filters["approval_status"]:
                continue
            if filters.get("supplier") and doc.linked_supplier != filters["supplier"]:
                continue
            for cov in doc.rm_coverage or []:
                rm = cov.rm_group
                if not rm:
                    continue
                if filters.get("rm_group") and rm != filters["rm_group"]:
                    continue
                rm_map.setdefault(rm, set()).add(doc.linked_supplier)
        rows = []
        for rm, sups in sorted(rm_map.items()):
            names = ", ".join(sorted(sups))
            rows.append(
                {
                    "view_as": "RM",
                    "rm_group": rm,
                    "supplier_count": len(sups),
                    "supplier_names": names,
                }
            )
        return rows

    # Coverage gaps
    covered = set()
    for sa_name in frappe.get_all("PEPL Supplier Approval", pluck="name"):
        doc = frappe.get_doc("PEPL Supplier Approval", sa_name)
        if doc.approval_status != "Approved":
            continue
        for cov in doc.rm_coverage or []:
            if cov.rm_group:
                covered.add(cov.rm_group)

    gaps = []
    for rm in frappe.get_all("PEPL RM Group", filters={"is_active": 1}, pluck="name"):
        if rm not in covered:
            gaps.append(
                {
                    "view_as": "Gaps",
                    "rm_group": rm,
                    "note": _("No Approved supplier rm_coverage row"),
                }
            )
    return gaps
