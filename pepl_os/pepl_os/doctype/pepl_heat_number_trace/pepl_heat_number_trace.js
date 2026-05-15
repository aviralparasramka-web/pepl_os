// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
// PEPL Heat Number Trace — form script

frappe.ui.form.on("PEPL Heat Number Trace", {
    refresh: function(frm) {
        if (frm.doc.current_status) {
            const colors = {
                "Available": "green",
                "In Production": "blue",
                "Fully Consumed": "gray",
                "Fully Dispatched": "gray",
                "Scrapped": "red",
                "Quarantine": "orange"
            };
            frm.dashboard.add_indicator(
                __("Status: {0}", [frm.doc.current_status]),
                colors[frm.doc.current_status] || "gray"
            );
            frm.dashboard.add_indicator(
                __("Available: {0}", [(frm.doc.current_qty_available || 0).toFixed(2)]),
                "blue"
            );
        }

        if (frm.doc.source_grn) {
            frm.add_custom_button(__("Source GRN"), () => {
                frappe.set_route("Form", "Purchase Receipt", frm.doc.source_grn);
            });
        }
        if (frm.doc.source_po) {
            frm.add_custom_button(__("Source PO"), () => {
                frappe.set_route("Form", "Purchase Order", frm.doc.source_po);
            });
        }
    }
});
