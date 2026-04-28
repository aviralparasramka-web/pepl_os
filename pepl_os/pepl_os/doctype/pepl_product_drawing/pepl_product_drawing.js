frappe.ui.form.on("PEPL Product Drawing", {
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

		if (!frm.is_new() && frm.doc.linked_product) {
			frm.add_custom_button(__("Load Components from BOM"), function() {
				frappe.call({
					method: "frappe.client.get_list",
					args: {
						doctype: "BOM",
						filters: {
							"item": frm.doc.linked_product,
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
							frappe.msgprint(__("No active default BOM found for this product. Create a BOM first."));
						}
					}
				});
			}, __("Actions"));
		}
	}
});
