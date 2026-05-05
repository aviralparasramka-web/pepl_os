frappe.ui.form.on("PEPL SO Document", {
	refresh(frm) {
		if (frm.doc.document_status) {
			const colours = {
				"Pending": "orange",
				"Received": "green",
				"Sent": "blue",
				"Filed": "darkgrey",
				"Obsolete": "grey"
			};
			frm.page.set_indicator(
				frm.doc.document_status,
				colours[frm.doc.document_status] || "grey"
			);
		}

		if (frm.doc.version_drift_flag) {
			frm.page.set_indicator("Version Drift Detected", "red");
		}
	}
});
