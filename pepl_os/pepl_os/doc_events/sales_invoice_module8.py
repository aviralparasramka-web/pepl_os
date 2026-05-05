import frappe
from frappe import _


def on_submit(doc, method=None):
    """Triggered when Sales Invoice is submitted.
    Module 8 action: auto-create Payment Tracker for this invoice.
    """
    try:
        from pepl_os.pepl_os.doctype.pepl_payment_tracker.pepl_payment_tracker import (
            create_payment_tracker_for_invoice,
        )
        result = create_payment_tracker_for_invoice(doc.name)

        if result.get("created"):
            frappe.msgprint(
                _("Payment Tracker {0} created (Sector: {1}, Invoice: \u20b9{2})").format(
                    result.get("tracker_name"),
                    result.get("sector"),
                    "{:,.2f}".format(float(result.get("invoice_amount") or 0))
                ),
                indicator="green",
                alert=True
            )

    except Exception as e:
        frappe.log_error(
            f"Module 8 Payment Tracker creation failed for SI {doc.name}: {str(e)}",
            "Module 8 Sales Invoice On Submit"
        )
