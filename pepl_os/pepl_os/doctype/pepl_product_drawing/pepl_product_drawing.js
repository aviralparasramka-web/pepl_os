frappe.ui.form.on("PEPL Product Drawing", {
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
					message: __("New revision added"),
					indicator: "blue"
				});
			}, __("Actions"));

			if (frm.doc.applies_to_products && frm.doc.applies_to_products.length > 0) {
				frm.add_custom_button(__("Load Components from BOM"), function() {
					const primary_product = frm.doc.applies_to_products.find(p => p.is_primary)
						|| frm.doc.applies_to_products[0];

					frappe.call({
						method: "frappe.client.get_list",
						args: {
							doctype: "BOM",
							filters: {
								"item": primary_product.applied_product,
								"is_active": 1,
								"is_default": 1
							},
							fields: ["name"]
						},
						callback: function(r) {
							if (r.message && r.message.length > 0) {
								const bom_name = r.message[0].name;
								frappe.call({
									method: "frappe.client.get",
									args: {
										doctype: "BOM",
										name: bom_name
									},
									callback: function(bom_r) {
										if (bom_r.message && bom_r.message.items) {
											frm.clear_table("components");
											bom_r.message.items.forEach(item => {
												const row = frm.add_child("components");
												row.component_item = item.item_code;
												row.qty_per_assembly = item.qty;
												row.uom = item.uom;
											});
											frm.refresh_field("components");
											frappe.show_alert({
												message: __("Loaded {0} components from BOM", [bom_r.message.items.length]),
												indicator: "green"
											});
										}
									}
								});
							} else {
								frappe.msgprint(__("No active default BOM found for primary product. Create a BOM first."));
							}
						}
					});
				}, __("Actions"));
			}
		}
	}
});

frappe.ui.form.on("PEPL Product Drawing Revision", {
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
