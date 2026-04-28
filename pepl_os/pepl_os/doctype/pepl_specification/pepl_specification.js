frappe.ui.form.on("PEPL Specification", {
	refresh(frm) {
		const status_colors = {
			"Draft": "grey",
			"Active": "green",
			"Under Review": "yellow",
			"Superseded": "orange",
			"Obsolete": "red"
		};
		if (frm.doc.status) {
			frm.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}
	}
});
