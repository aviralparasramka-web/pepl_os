frappe.ui.form.on("PEPL Item Drawing", {
	refresh(frm) {
		const status_colors = {
			"Draft": "grey",
			"Active": "green",
			"Superseded": "orange",
			"Obsolete": "red"
		};
		if (frm.doc.status) {
			frm.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}
	}
});
