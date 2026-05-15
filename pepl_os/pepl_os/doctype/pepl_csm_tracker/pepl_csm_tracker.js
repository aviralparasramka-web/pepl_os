// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
// PEPL CSM Tracker — form script

frappe.ui.form.on("PEPL CSM Tracker", {
    refresh: function(frm) {
        // Reconciliation status indicator on the form header
        if (frm.doc.reconciliation_status) {
            const colors = {
                "Reconciled": "green",
                "Pending Customer Confirmation": "orange",
                "Mismatch": "red"
            };
            frm.dashboard.add_indicator(
                __("Reconciliation: {0}", [frm.doc.reconciliation_status]),
                colors[frm.doc.reconciliation_status] || "gray"
            );
        }
        if (frm.doc.rows_pending_customer_confirmation > 0) {
            frm.dashboard.add_indicator(
                __("Pending customer weight: {0} row(s)", [frm.doc.rows_pending_customer_confirmation]),
                "orange"
            );
        }

        // Disposition action buttons (visible when CSM is Active or Pending Disposition)
        if (frm.doc.status === "Active" || frm.doc.status === "Pending Disposition") {
            frm.add_custom_button(__("Record Scrap Return"), () => pepl_csm_record_return(frm, "Scrap return"), __("Disposition"));
            frm.add_custom_button(__("Record Rejected Pieces Return"), () => pepl_csm_record_return(frm, "Rejected pieces return"), __("Disposition"));
            frm.add_custom_button(__("Record Excess Material Return"), () => pepl_csm_record_return(frm, "Excess material return"), __("Disposition"));
            frm.add_custom_button(__("Mark Reconciled"), () => pepl_csm_mark_status(frm, "Reconciled"), __("Disposition"));
            frm.add_custom_button(__("Close CSM Tracker"), () => pepl_csm_mark_status(frm, "Closed"), __("Disposition"));
        }

        // Linked SO shortcut
        if (frm.doc.linked_so) {
            frm.add_custom_button(__("Open Sales Order"), () => {
                frappe.set_route("Form", "Sales Order", frm.doc.linked_so);
            });
        }
    }
});


function pepl_csm_record_return(frm, return_type) {
    const d = new frappe.ui.Dialog({
        title: __("Record Return: ") + return_type,
        fields: [
            {fieldname: "qty_returned", fieldtype: "Float", label: "Qty Returned", reqd: 1},
            {fieldname: "return_uom", fieldtype: "Select", label: "Return UOM",
             options: "kg\nnos\nm\nsqm\nlt", default: frm.doc.material_uom, reqd: 1},
            {fieldname: "customer_document_reference", fieldtype: "Data", label: "Customer Return Challan Ref"},
            {fieldname: "remarks", fieldtype: "Small Text", label: "Remarks"}
        ],
        primary_action_label: "Record",
        primary_action(values) {
            frappe.call({
                method: "pepl_os.pepl_os.api.csm_tracker.record_return",
                args: {
                    csm_name: frm.doc.name,
                    return_type: return_type,
                    qty_returned: values.qty_returned,
                    return_uom: values.return_uom,
                    customer_document_reference: values.customer_document_reference,
                    remarks: values.remarks
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __("Return recorded. Balance: ") + (r.message.balance_now || 0).toFixed(2),
                            indicator: "green"
                        });
                        d.hide();
                        frm.reload_doc();
                    }
                }
            });
        }
    });
    d.show();
}


function pepl_csm_mark_status(frm, new_status) {
    frappe.confirm(
        __("Set status to ") + new_status + "?",
        function() {
            frappe.call({
                method: "pepl_os.pepl_os.api.csm_tracker.mark_status",
                args: {csm_name: frm.doc.name, new_status: new_status},
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({message: __("Status: ") + new_status, indicator: "blue"});
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}
