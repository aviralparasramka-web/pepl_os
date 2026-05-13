# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class PEPLQuotationComparison(Document):
    def validate(self):
        self._compute_summary()
        self._compute_item_amounts()
        self._compute_variance_per_item()
        self._validate_override_reasons()

    def _compute_summary(self):
        """Set item_count, vendor_count, total_award_value."""
        self.item_count = len(self.comparison_items or [])

        vendors = set()
        total = 0.0
        for row in (self.comparison_items or []):
            if row.selected_vendor:
                vendors.add(row.selected_vendor)
            if row.selected_vendor and row.selected_rate and row.qty:
                total += flt(row.qty) * flt(row.selected_rate)

        self.vendor_count = len(vendors)
        self.total_award_value = total

    def _compute_item_amounts(self):
        """For each item row, set amount = qty × selected_rate."""
        for row in (self.comparison_items or []):
            if row.qty and row.selected_rate:
                row.amount = flt(row.qty) * flt(row.selected_rate)
            else:
                row.amount = 0.0

    def _compute_variance_per_item(self):
        """For each item, set variance_pct = (selected_rate - original_quoted_rate)
        / original_quoted_rate × 100. If original is 0 or None, skip."""
        for row in (self.comparison_items or []):
            orig = flt(row.original_quoted_rate)
            if not orig:
                row.variance_pct = 0.0
                continue
            row.variance_pct = ((flt(row.selected_rate) - orig) / orig) * 100.0

    def _validate_override_reasons(self):
        """For each item where selected_rate differs from original_quoted_rate
        by more than 0.01, require override_reason. Throw if missing."""
        missing = []
        for row in (self.comparison_items or []):
            orig = flt(row.original_quoted_rate)
            sel = flt(row.selected_rate)
            if orig and abs(sel - orig) > 0.01 and not row.override_reason:
                missing.append(row.item_code or f"Row {row.idx}")

        if missing:
            frappe.throw(
                _("Override Reason is required for items with rate changes: {0}").format(
                    ", ".join(missing)
                )
            )
