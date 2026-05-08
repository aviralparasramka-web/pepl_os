"""LEGAL / COMPLIANCE: MSME 45-day payment orientation (indicative — verify with counsel)."""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Bill Number"), "fieldname": "bill", "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
        {"label": _("MSME Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": _("MSME Certificate No"), "fieldname": "msme_cert", "fieldtype": "Data", "width": 140},
        {"label": _("Bill Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 100},
        {"label": _("Days Since Bill"), "fieldname": "days_since", "fieldtype": "Int", "width": 110},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
        {"label": _("Est. Interest Liability (indicative)"), "fieldname": "interest_hint", "fieldtype": "Currency", "width": 160},
    ]


def _as_list(val):
    if val is None or val == "":
        return []
    return list(val) if isinstance(val, (list, tuple)) else [val]


def get_data(filters):
    cols = frappe.db.get_table_columns("Supplier") or []
    has_msme = "custom_is_msme" in cols
    has_cert = "custom_msme_certificate_no" in cols

    if not has_msme:
        return [
            {
                "bill": None,
                "supplier_name": _("Configure Supplier field custom_is_msme (Check) to enable this legal report."),
                "msme_cert": _("—"),
                "bill_date": None,
                "days_since": None,
                "status": _("Not configured"),
                "interest_hint": None,
            }
        ]

    as_of = getdate(filters.get("as_of_date") or today())

    rows = frappe.db.sql(
        """
        SELECT pi.name AS bill,
               pi.supplier AS supplier,
               pi.posting_date AS bill_date,
               pi.outstanding_amount AS outstanding
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
          AND IFNULL(pi.outstanding_amount, 0) > 0.005
        """,
        as_dict=True,
    )

    out = []
    for r in rows:
        is_msme = frappe.db.get_value("Supplier", r.supplier, "custom_is_msme")
        if not is_msme:
            continue

        sn = frappe.db.get_value("Supplier", r.supplier, "supplier_name") or r.supplier
        cert = ""
        if has_cert:
            cert = frappe.db.get_value("Supplier", r.supplier, "custom_msme_certificate_no") or ""

        days = date_diff(as_of, r.bill_date) if r.bill_date else 0
        if days < 40:
            status = "Compliant"
            interest = 0
        elif days <= 45:
            status = "Approaching Breach"
            interest = 0
        else:
            status = "Breached"
            interest = flt(r.outstanding) * 0.03 * max(0, days - 45) / 365

        if filters.get("supplier") and r.supplier != filters["supplier"]:
            continue
        pick = _as_list(filters.get("status"))
        if pick and status not in pick:
            continue

        out.append(
            {
                "bill": r.bill,
                "supplier_name": sn,
                "msme_cert": cert or _("— configure Supplier.custom_msme_certificate_no"),
                "bill_date": r.bill_date,
                "days_since": days,
                "status": status,
                "interest_hint": interest,
            }
        )
    return out
