frappe.ui.form.on("PEPL Item Drawing", {
	refresh(frm) {
		const status_colors = {
			"Active": "green",
			"Obsolete": "red"
		};
		if (frm.doc.status) {
			frm.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Add New Revision"), function() {
				const new_row = frm.add_child("revisions");
				new_row.is_current = 1;
				new_row.issue_date = frappe.datetime.get_today();

				(frm.doc.revisions || []).forEach(r => {
					if (r.name !== new_row.name) {
						r.is_current = 0;
					}
				});

				frm.refresh_field("revisions");
				frappe.show_alert({
					message: __("New revision added — attach the file and update revision letter"),
					indicator: "blue"
				});
			}, __("Actions"));
		}
	}
});

frappe.ui.form.on("PEPL Item Drawing Revision", {
	is_current(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.is_current) {
			(frm.doc.revisions || []).forEach(r => {
				if (r.name !== cdn) {
					frappe.model.set_value(r.doctype, r.name, "is_current", 0);
				}
			});
		}
	}
});
