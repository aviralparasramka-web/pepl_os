frappe.ui.form.on("PEPL RM Group", {
	refresh(frm) {
		if (frm.doc.is_active) {
			frm.set_indicator("Active", "green");
		} else {
			frm.set_indicator("Inactive", "grey");
		}
	}
});
