frappe.ui.form.on("Vendor Approval Status", {
    refresh(frm) {
        // Show stage indicator
        if (frm.doc.sector === "Railways" && frm.doc.railways_stage) {
            const colors = {
                "Unapproved": "red",
                "Developmental": "orange",
                "Approved": "green"
            };
            frm.set_indicator(frm.doc.railways_stage, colors[frm.doc.railways_stage]);
        } else if (frm.doc.sector === "Defence" && frm.doc.defence_stage) {
            const colors = {
                "Source Development": "orange",
                "Approved / Established": "green"
            };
            frm.set_indicator(frm.doc.defence_stage, colors[frm.doc.defence_stage]);
        }

        // Show required documents button
        if (frm.doc.sector && (frm.doc.railways_stage || frm.doc.defence_stage)) {
            frm.add_custom_button(__("Show Required Documents"), function() {
                frappe.call({
                    method: "pepl_os.doctype.vendor_approval_status.vendor_approval_status.get_required_documents",
                    args: {
                        sector: frm.doc.sector,
                        stage: frm.doc.sector === "Railways" ? frm.doc.railways_stage : frm.doc.defence_stage
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            const docs_list = r.message.map(d => `<li>${d}</li>`).join("");
                            frappe.msgprint({
                                title: __("Required Documents for This Stage"),
                                message: `<ul>${docs_list}</ul>`,
                                indicator: "blue"
                            });
                        } else {
                            frappe.msgprint(__("No specific documents required for this combination."));
                        }
                    }
                });
            });
        }
    },

    sector(frm) {
        // Clear opposite sector stage when sector changes
        if (frm.doc.sector === "Railways") {
            frm.set_value("defence_stage", "");
        } else if (frm.doc.sector === "Defence") {
            frm.set_value("railways_stage", "");
        }
    }
});