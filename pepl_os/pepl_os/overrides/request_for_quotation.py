# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

"""
RFQ override: auto-populate Suppliers child table from per-item target_vendors,
warn on non-approved vendors, and defer the standard email send when Phase 2
target_vendors are present.
"""

import frappe
from frappe import _
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import (
    RequestforQuotation,
)


def _target_vendors_installed() -> bool:
    return frappe.get_meta("Request for Quotation Item").has_field("target_vendors")


class PeplRequestForQuotation(RequestforQuotation):
    # ------------------------------------------------------------------
    # validate: called on every save and on submit
    # ------------------------------------------------------------------
    def validate(self):
        super().validate()
        if _target_vendors_installed():
            self._phase2_sync_suppliers()
            self._phase2_warn_non_approved()

    # ------------------------------------------------------------------
    # on_submit: skip standard bulk-send when Phase 2 target_vendors exist
    # ------------------------------------------------------------------
    def on_submit(self):
        self.db_set("status", "Submitted")
        for supplier in self.suppliers:
            supplier.email_sent = 0
            supplier.quote_status = "Pending"

        if _target_vendors_installed() and self._has_phase2_selections():
            # Emails are sent manually via "Send RFQ to Vendors" button
            return

        self.send_to_supplier()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _has_phase2_selections(self) -> bool:
        """Return True if any RFQ item has at least one target_vendors entry."""
        for it in self.items or []:
            if it.item_code and (it.get("target_vendors") or []):
                return True
        return False

    def _phase2_sync_suppliers(self):
        """Rebuild RFQ.suppliers from the union of target_vendors across all items.

        Idempotent: clears and rebuilds every time.
        Does nothing if no item has any target_vendors configured (preserves
        manual supplier rows added via the standard Suppliers child table).
        """
        collected = []
        seen = set()
        for it in self.items or []:
            if not it.item_code:
                continue
            for tv in it.get("target_vendors") or []:
                sup = tv.supplier
                if not sup or sup in seen:
                    continue
                seen.add(sup)
                collected.append(sup)

        if not collected:
            return  # No target_vendors set — leave Suppliers child table untouched

        self.set("suppliers", [])
        for sup in collected:
            sup_name = frappe.db.get_value("Supplier", sup, "supplier_name") or sup
            email_id = frappe.db.get_value("Supplier", sup, "email_id") or ""
            self.append(
                "suppliers",
                {
                    "supplier": sup,
                    "supplier_name": sup_name,
                    "email_id": email_id,
                },
            )

    def _phase2_warn_non_approved(self):
        """Show a non-blocking alert if any target_vendors entry is not Approved."""
        for it in self.items or []:
            if not it.item_code:
                continue
            for tv in it.get("target_vendors") or []:
                sup = tv.supplier
                if not sup:
                    continue
                status = frappe.db.get_value(
                    "PEPL Supplier Approval",
                    {"linked_supplier": sup},
                    "approval_status",
                )
                if status != "Approved":
                    frappe.msgprint(
                        _(
                            "Item {0}: vendor {1} is not formally approved "
                            "(PEPL Supplier Approval status: {2}). "
                            "This will be logged on submit."
                        ).format(
                            it.item_code,
                            sup,
                            status or _("No Approval Record"),
                        ),
                        indicator="orange",
                        alert=True,
                    )
