frappe.ui.form.on("PEPL Document Tracker", {
	refresh(frm) {
		if (frm.doc.total_documents !== undefined) {
			frm.page.set_indicator(
				`${frm.doc.total_documents} Document(s)`,
				frm.doc.total_documents > 0 ? "blue" : "grey"
			);
		}
	}
});
