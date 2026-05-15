// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
// PEPL Receipt Log — form script

frappe.ui.form.on("PEPL Receipt Log", {
    refresh: function(frm) {
        // Status indicators
        if (frm.doc.documents_status) {
            const colors = {
                "Complete": "green",
                "Pending Items": "orange",
                "Not Started": "gray",
                "Expired": "red"
            };
            frm.dashboard.add_indicator(
                __("Docs: {0}", [frm.doc.documents_status]),
                colors[frm.doc.documents_status] || "gray"
            );
        }
        if (frm.doc.qc_status) {
            const qc_colors = {
                "Passed": "green",
                "Failed": "red",
                "Pending": "orange",
                "Not Required": "blue"
            };
            frm.dashboard.add_indicator(
                __("QC: {0}", [frm.doc.qc_status]),
                qc_colors[frm.doc.qc_status] || "gray"
            );
        }
        if (frm.doc.pending_doc_count > 0) {
            frm.dashboard.add_indicator(
                __("{0} document(s) pending", [frm.doc.pending_doc_count]),
                "orange"
            );
        }

        // Navigation shortcuts
        if (frm.doc.linked_purchase_receipt) {
            frm.add_custom_button(__("Open Purchase Receipt"), () => {
                frappe.set_route("Form", "Purchase Receipt", frm.doc.linked_purchase_receipt);
            });
        }
        if (frm.doc.heat_number) {
            frm.add_custom_button(__("View Heat Trace"), () => {
                frappe.set_route("Form", "PEPL Heat Number Trace", frm.doc.heat_number);
            });
        }
    }
});
