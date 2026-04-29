import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate, today, flt


class PEPLTender(Document):
    def autoname(self):
        self.tender_no = make_autoname("TND-.YYYY.-.####")
        self.name = self.tender_no

    def validate(self):
        if self.customer_group and not self.sub_sector:
            cg = self.customer_group
            mapping = {
                "Railways - Loco": "Railways - Loco",
                "Railways - Coaches": "Railways - Coaches",
                "Railways - Zonal": "Railways - Zonal",
                "Defence - MIL": "Defence - MIL",
                "Defence - YIL": "Defence - YIL",
                "Defence - AWEIL": "Defence - AWEIL",
                "Defence - Private": "Defence - Private",
                "Private Sector": "Private Sector",
                "PSU": "PSU",
            }
            if cg in mapping:
                self.sub_sector = mapping[cg]

        if self.customer_group and not self.sector:
            if "Railways" in self.customer_group:
                self.sector = "Railways"
            elif "Defence" in self.customer_group:
                self.sector = "Defence"
            elif "Private" in self.customer_group:
                self.sector = "Private"
            else:
                self.sector = "Others"

        if self.items:
            for item_row in self.items:
                if item_row.item and self.sector:
                    self._fetch_item_details(item_row)

        self._calculate_summary()
        self._update_overall_status()

        if self.status in ["Lost", "Won", "Partially Won"]:
            if not self.technical_qualified:
                frappe.msgprint(
                    _("Please set Technical Qualification status for outcomes."),
                    indicator="orange",
                    alert=True,
                )

        if self.bid_submission_deadline and self.is_new():
            if getdate(self.bid_submission_deadline) < getdate(today()):
                frappe.msgprint(
                    _("Bid deadline {0} is in the past — please verify").format(
                        self.bid_submission_deadline
                    ),
                    indicator="orange",
                    alert=True,
                )

    def _fetch_item_details(self, item_row):
        """Fetch drawing, spec, and vendor approval stage for an item row.
        Updated to query PEPL Product Master instead of separate drawing/spec DocTypes."""

        product = frappe.db.get_value(
            "PEPL Product Master",
            {"linked_item": item_row.item},
            ["name", "current_drawing_revision", "drawing_number"],
            as_dict=True,
        )

        if product:
            item_row.current_drawing_revision = product.current_drawing_revision

            primary_spec = frappe.db.sql(
                """
                SELECT spec_title FROM `tabPEPL Product Specification`
                WHERE parent = %s AND status = 'Active'
                ORDER BY creation ASC LIMIT 1
                """,
                product.name,
                as_dict=True,
            )

            if primary_spec:
                item_row.current_specification = primary_spec[0].spec_title

        vas = frappe.db.get_value(
            "Vendor Approval Status",
            {"item": item_row.item, "sector": self.sector},
            ["railways_stage", "defence_stage"],
            as_dict=True,
        )
        if vas:
            if self.sector == "Railways":
                item_row.vendor_approval_stage = vas.railways_stage or "Unapproved"
            elif self.sector == "Defence":
                item_row.vendor_approval_stage = vas.defence_stage or "Source Development"
        else:
            item_row.vendor_approval_stage = "No Record"

    def _calculate_summary(self):
        """Auto-calculate totals and win/loss counts from line items."""
        if not self.items:
            return

        self.total_estimated_value = sum(flt(i.estimated_total_value) for i in self.items)
        self.total_bid_value = sum(flt(i.our_bid_total_value) for i in self.items)
        self.items_won = sum(1 for i in self.items if i.outcome == "Won")
        self.items_lost = sum(1 for i in self.items if i.outcome == "Lost")

        total_decided = self.items_won + self.items_lost
        self.win_rate = (self.items_won / total_decided * 100) if total_decided > 0 else 0

    def _update_overall_status(self):
        """Derive tender-level status from item-level outcomes."""
        if not self.items:
            return

        outcomes = [i.outcome for i in self.items if i.outcome]
        if not outcomes:
            return

        if all(o == "Won" for o in outcomes) and len(outcomes) == len(self.items):
            self.status = "Won"
        elif all(o == "Lost" for o in outcomes) and len(outcomes) == len(self.items):
            self.status = "Lost"
        elif "Won" in outcomes and "Lost" in outcomes:
            self.status = "Partially Won"


@frappe.whitelist()
def auto_populate_bid_documents(tender_name):
    """Auto-populate bid documents based on items' Vendor Approval Status.
    Called from the Tender form via custom button."""

    tender = frappe.get_doc("PEPL Tender", tender_name)

    if not tender.items:
        frappe.throw(_("Add tender items first before generating document checklist"))

    sector = tender.sector
    if not sector:
        frappe.throw(_("Sector must be set on tender"))

    stages_seen = set()
    for item_row in tender.items:
        if item_row.vendor_approval_stage:
            stages_seen.add(item_row.vendor_approval_stage)

    from pepl_os.pepl_os.doctype.vendor_approval_status.vendor_approval_status import (
        get_required_documents,
    )

    all_required_docs = set()
    for stage in stages_seen:
        if stage and stage != "No Record":
            required = get_required_documents(sector, stage)
            if isinstance(required, list):
                all_required_docs.update(required)

    existing_doc_types = {d.document_type for d in tender.bid_documents}
    added = 0
    for doc_type in all_required_docs:
        if doc_type not in existing_doc_types:
            tender.append(
                "bid_documents",
                {
                    "document_source": "Auto-Required",
                    "document_type": doc_type,
                    "is_mandatory": 1,
                    "is_attached": 0,
                },
            )
            added += 1

    tender.save()
    return {"added": added, "total_required": len(all_required_docs)}


@frappe.whitelist()
def get_tender_summary(filters=None):
    """Returns aggregated tender pipeline summary for dashboards."""

    summary = frappe.db.sql(
        """
        SELECT
            sector,
            status,
            COUNT(*) as count,
            SUM(total_estimated_value) as total_estimated,
            SUM(total_bid_value) as total_bid,
            SUM(items_won) as items_won_count
        FROM `tabPEPL Tender`
        GROUP BY sector, status
        ORDER BY sector, status
        """,
        as_dict=True,
    )

    return summary
