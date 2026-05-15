# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
# PEPL CSM Tracker — server-side functions and doc_events hooks.

import frappe
import json
from frappe import _
from frappe.utils import nowdate, now_datetime, flt


def auto_create_on_so_submit(doc, method):
    """Sales Order on_submit hook: auto-create CSM Tracker if
    csm_terms is set on the SO (custom field) and not 'Not Applicable'."""
    try:
        # Read csm_terms from any of: unprefixed, custom_ prefix
        # (Frappe Cloud auto-adds custom_ prefix to manually created
        # custom fields), or full prefixed variant.
        csm_terms = (
            getattr(doc, "csm_terms", None)
            or getattr(doc, "custom_csm_terms", None)
            or None
        )
        if not csm_terms or csm_terms == "Not Applicable":
            return

        # Idempotency: skip if already exists for this SO
        existing = frappe.db.get_value(
            "PEPL CSM Tracker",
            {"linked_so": doc.name},
            "name",
        )
        if existing:
            return

        csm = frappe.new_doc("PEPL CSM Tracker")
        csm.linked_so = doc.name
        csm.customer = doc.customer
        csm.csm_terms = csm_terms
        csm.status = "Active"
        # Sensible defaults — user will refine in form
        csm.material_uom = "kg"
        csm.product_uom = "nos"
        csm.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"auto_create_on_so_submit failed for SO {doc.name}: {e}",
            "CSM Tracker Hook",
        )


def auto_consume_on_dn_submit(doc, method):
    """Delivery Note on_submit hook: for each DN item, append a
    Consumption row on the linked CSM Tracker.

    Stores must edit the auto-created row to fill dispatched_weight_pepl
    after dispatch is weighed."""
    try:
        # Find SO references on DN items
        so_names = set()
        for item in (doc.items or []):
            so = getattr(item, "against_sales_order", None) or getattr(item, "sales_order", None)
            if so:
                so_names.add(so)

        if not so_names:
            return

        for so_name in so_names:
            csm_name = frappe.db.get_value(
                "PEPL CSM Tracker",
                {"linked_so": so_name, "status": ["!=", "Closed"]},
                "name",
            )
            if not csm_name:
                continue

            csm = frappe.get_doc("PEPL CSM Tracker", csm_name)

            # Idempotency: skip if a consumption row for this DN already exists
            already_logged = any(
                r.linked_delivery_note == doc.name
                for r in (csm.consumption or [])
            )
            if already_logged:
                continue

            # Sum pieces dispatched across DN items linked to this SO
            pieces = 0
            for item in (doc.items or []):
                so = getattr(item, "against_sales_order", None) or getattr(item, "sales_order", None)
                if so == so_name:
                    pieces += flt(item.qty)

            csm.append("consumption", {
                "consumption_date": doc.posting_date or nowdate(),
                "linked_delivery_note": doc.name,
                "pieces_dispatched": pieces,
                "dispatched_weight_pepl": 0,  # Stores fills this after weighing
                "weight_status": "Pending Customer Confirmation",
                "remarks": "Auto-created on DN submit. Update dispatched_weight_pepl after weighing.",
            })
            csm.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"auto_consume_on_dn_submit failed for DN {doc.name}: {e}",
            "CSM Tracker Hook",
        )


def warn_on_si_submit(doc, method):
    """Sales Invoice on_submit hook: warn if linked SO has a CSM
    Tracker that is not yet Reconciled. Warning only, never blocks."""
    try:
        if not (doc.items or []):
            return

        so_names = set()
        for item in doc.items:
            so = getattr(item, "sales_order", None)
            if so:
                so_names.add(so)

        warnings = []
        for so_name in so_names:
            csm_name = frappe.db.get_value(
                "PEPL CSM Tracker",
                {"linked_so": so_name},
                "name",
            )
            if not csm_name:
                continue
            csm = frappe.get_doc("PEPL CSM Tracker", csm_name)
            if csm.reconciliation_status != "Reconciled":
                warnings.append({
                    "so": so_name,
                    "csm": csm_name,
                    "status": csm.reconciliation_status,
                    "balance": flt(csm.balance_unaccounted),
                    "pending_rows": int(csm.rows_pending_customer_confirmation or 0),
                })

        if warnings:
            msg_lines = [_("CSM reconciliation is not complete for:")]
            for w in warnings:
                msg_lines.append(
                    f"  \u2022 {w['csm']} (SO: {w['so']}) \u2014 {w['status']}; "
                    f"balance: {w['balance']:.2f}; "
                    f"pending rows: {w['pending_rows']}"
                )
            msg_lines.append(_("This is a warning. The invoice is being submitted anyway."))

            # Persist warning to audit log on each CSM Tracker
            for w in warnings:
                csm = frappe.get_doc("PEPL CSM Tracker", w["csm"])
                log = json.loads(csm.closure_warnings_log or "[]")
                log.append({
                    "trigger": "Sales Invoice submit",
                    "trigger_doc": doc.name,
                    "status_at_warning": w["status"],
                    "balance_at_warning": w["balance"],
                    "user": frappe.session.user,
                    "ts": str(now_datetime()),
                })
                csm.closure_warnings_log = json.dumps(log, default=str)
                csm.save(ignore_permissions=True)

            frappe.msgprint(
                "\n".join(msg_lines),
                title=_("CSM Reconciliation Warning"),
                indicator="orange",
            )
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"warn_on_si_submit failed for SI {doc.name}: {e}",
            "CSM Tracker Hook",
        )


@frappe.whitelist()
def record_return(csm_name, return_type, qty_returned, return_uom, customer_document_reference=None, remarks=None):
    """Record a Return row on the CSM Tracker. Called from form JS
    via the disposition action buttons."""
    csm = frappe.get_doc("PEPL CSM Tracker", csm_name)
    if csm.status == "Closed":
        frappe.throw(_("Cannot modify Closed CSM Tracker."))

    csm.append("returns", {
        "return_date": nowdate(),
        "return_type": return_type,
        "qty_returned": flt(qty_returned),
        "return_uom": return_uom,
        "customer_document_reference": customer_document_reference or "",
        "remarks": remarks or "",
    })
    csm.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "recorded", "balance_now": flt(csm.balance_unaccounted)}


@frappe.whitelist()
def mark_status(csm_name, new_status):
    """Manual status transition from form JS."""
    if new_status not in ("Active", "Pending Disposition", "Reconciled", "Closed"):
        frappe.throw(_("Invalid status: {0}").format(new_status))
    csm = frappe.get_doc("PEPL CSM Tracker", csm_name)
    csm.status = new_status
    csm.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "updated", "new_status": new_status}
