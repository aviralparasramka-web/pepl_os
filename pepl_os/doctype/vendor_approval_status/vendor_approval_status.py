import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class VendorApprovalStatus(Document):
    def validate(self):
        # Sector-specific stage validation
        if self.sector == "Railways":
            if not self.railways_stage:
                frappe.throw(_("Railways Approval Stage is required when sector is Railways"))
            self.defence_stage = None
        elif self.sector == "Defence":
            if not self.defence_stage:
                frappe.throw(_("Defence Approval Stage is required when sector is Defence"))
            self.railways_stage = None

        # Approval reference recommended if approved
        if self.sector == "Railways" and self.railways_stage in ["Developmental", "Approved"]:
            if not self.approval_reference:
                frappe.msgprint(
                    _("Approval reference number recommended for {0} stage").format(self.railways_stage),
                    indicator="orange",
                    alert=True
                )

        if self.sector == "Defence" and self.defence_stage == "Approved / Established":
            if not self.approval_reference:
                frappe.msgprint(
                    _("Approval reference number recommended for Approved / Established stage"),
                    indicator="orange",
                    alert=True
                )

        # Warn if any document is expired
        if self.vendor_approval_documents:
            for doc in self.vendor_approval_documents:
                if doc.expiry_date and getdate(doc.expiry_date) < getdate(today()):
                    frappe.msgprint(
                        _("Document {0} expired on {1}").format(
                            doc.document_type, doc.expiry_date
                        ),
                        indicator="red",
                        alert=True
                    )


@frappe.whitelist()
def get_required_documents(sector, stage):
    """Returns list of required documents for given sector and approval stage.
    Used by Tender Management to auto-generate document checklist."""

    base_docs = [
        "Udyam Aadhaar",
        "GST Certificate",
        "PAN Card",
        "QAP",
        "Plant and Machinery List",
        "Instruments and Testing Facilities List"
    ]

    if sector == "Railways":
        if stage == "Unapproved":
            return base_docs
        elif stage == "Developmental":
            return base_docs + [
                "QAP Approval Letter",
                "CCA Approval Letter",
                "Final IC"
            ]
        elif stage == "Approved":
            return ["Approval Certificate"]

    elif sector == "Defence":
        if stage == "Source Development":
            return base_docs
        elif stage == "Approved / Established":
            return ["Last I-Note", "60% Tender Completion Evidence"]

    return []


@frappe.whitelist()
def get_approval_status_for_item(item, sector):
    """Fetch the current approval status for an Item in given sector.
    Used by Tender Management when a new tender is created."""

    record = frappe.db.get_value(
        "Vendor Approval Status",
        {"item": item, "sector": sector},
        ["name", "railways_stage", "defence_stage", "approval_date", "approval_reference"],
        as_dict=True
    )

    if not record:
        return {
            "exists": False,
            "stage": None,
            "message": f"No approval record found for {item} in {sector} sector"
        }

    stage = record.railways_stage if sector == "Railways" else record.defence_stage

    return {
        "exists": True,
        "name": record.name,
        "stage": stage,
        "approval_date": record.approval_date,
        "approval_reference": record.approval_reference,
        "required_documents": get_required_documents(sector, stage)
    }