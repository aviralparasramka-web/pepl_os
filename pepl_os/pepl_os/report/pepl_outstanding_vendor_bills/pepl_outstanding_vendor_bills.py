"""Outstanding Purchase Invoices (vendor bills) — MSME-oriented buckets."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Bill Number"), "fieldname": "bill", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
        {"label": _("Bill Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 100},
        {"label": _("Net Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
        {"label": _("Days Outstanding"), "fieldname": "days_outstanding", "fieldtype": "Int", "width": 120},
        {"label": _("MSME Status"), "fieldname": "msme_status", "fieldtype": "Data", "width": 110},
        {"label": _("MSME Compliance Bucket"), "fieldname": "msme_bucket", "fieldtype": "Data", "width": 180},
        {"label": _("Payment Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 120},
    ]


def _as_list(val):
    if val is None or val == "":
        return []
    return list(val) if isinstance(val, (list, tuple)) else [val]


def get_data(filters):
    cols = frappe.db.get_table_columns("Supplier") or []
    has_msme = "custom_is_msme" in cols

    rows = frappe.db.sql(
        """
        SELECT pi.name AS bill,
               pi.supplier AS supplier,
               pi.posting_date AS bill_date,
               pi.outstanding_amount AS outstanding,
               pi.due_date AS due_date
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1
          AND IFNULL(pi.outstanding_amount, 0) > 0.005
        ORDER BY pi.posting_date ASC
        """,
        as_dict=True,
    )

    out = []
    for r in rows:
        days = date_diff(getdate(today()), r.bill_date) if r.bill_date else 0
        msme_flag = frappe.db.get_value("Supplier", r.supplier, "custom_is_msme")
        if filters.get("msme_only") and not msme_flag:
            continue

        suppliers_f = _as_list(filters.get("supplier"))
        if suppliers_f and r.supplier not in suppliers_f:
            continue

        msme_status = ""
        if has_msme:
            msme_status = msme_flag or ""
            if isinstance(msme_status, int):
                msme_status = "Yes" if msme_status else "No"
        else:
            msme_status = _("Not configured — add Supplier.custom_is_msme")

        bucket = _msme_bucket(days)

        buckets_f = _as_list(filters.get("msme_bucket"))
        if buckets_f and bucket not in buckets_f:
            continue

        out.append(
            {
                "bill": r.bill,
                "supplier": r.supplier,
                "bill_date": r.bill_date,
                "outstanding": r.outstanding,
                "days_outstanding": days,
                "msme_status": msme_status,
                "msme_bucket": bucket,
                "due_date": r.due_date,
            }
        )
    return out


def _msme_bucket(days):
    d = int(days or 0)
    if d <= 35:
        return "Within 45 days"
    if d <= 44:
        return "Approaching 45 days"
    return "OVERDUE — legal exposure"
