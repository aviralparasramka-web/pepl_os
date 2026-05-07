// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

frappe.ui.form.on("PEPL Purchase Tracker", {
	refresh(frm) {
		const colors = {
			"PO Sent": "orange",
			Acknowledged: "yellow",
			"Material Dispatched": "blue",
			Received: "purple",
			"Inspected - Pass": "green",
			"Inspected - Fail": "red",
			Closed: "darkgrey",
		};
		if (frm.doc.current_status) {
			frm.page.set_indicator(frm.doc.current_status, colors[frm.doc.current_status] || "grey");
		}
	},
});
