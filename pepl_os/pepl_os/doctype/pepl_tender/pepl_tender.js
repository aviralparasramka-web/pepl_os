frappe.ui.form.on("PEPL Tender", {
	refresh(frm) {
		const status_colors = {
			"Active Bid": "blue",
			"Submitted": "yellow",
			"Won": "green",
			"Partially Won": "green",
			"Order Received": "purple",
			"Lost": "red",
			"No Bid": "grey",
			"Cancelled": "grey",
			"Re-tendered": "orange"
		};
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}

		// Deadline urgency indicator
		if (frm.doc.bid_submission_deadline && frm.doc.status === "Active Bid") {
			const deadline = frappe.datetime.str_to_obj(frm.doc.bid_submission_deadline);
			const now = new Date();
			const days_left = Math.floor((deadline - now) / (1000 * 60 * 60 * 24));

			if (days_left < 0) {
				frm.dashboard.add_indicator(__("DEADLINE PASSED"), "red");
			} else if (days_left <= 1) {
				frm.dashboard.add_indicator(__("Deadline in {0} day(s)", [days_left]), "red");
			} else if (days_left <= 3) {
				frm.dashboard.add_indicator(__("Deadline in {0} days", [days_left]), "orange");
			} else if (days_left <= 7) {
				frm.dashboard.add_indicator(__("Deadline in {0} days", [days_left]), "yellow");
			}
		}

		// Auto-Generate Document Checklist button
		if (!frm.is_new() && frm.doc.items && frm.doc.items.length > 0) {
			frm.add_custom_button(__("Auto-Generate Document Checklist"), function() {
				frappe.call({
					method: "pepl_os.pepl_os.doctype.pepl_tender.pepl_tender.auto_populate_bid_documents",
					args: { tender_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Added {0} required documents to checklist (total {1})",
									[r.message.added, r.message.total_required]),
								indicator: "green"
							});
							frm.reload_doc();
						}
					}
				});
			}, __("Documents"));
		}

		// CREATE SALES ORDER button — Module 4 automation
		const can_create_so = !frm.is_new()
			&& (frm.doc.status === "Won" || frm.doc.status === "Partially Won")
			&& frm.doc.customer_po_received === 1
			&& frm.doc.po_number
			&& !frm.doc.linked_sales_order;

		if (can_create_so) {
			frm.add_custom_button(__("Create Sales Order"), function() {
				const won_count = (frm.doc.items || []).filter(i => i.outcome === "Won").length;

				frappe.confirm(
					__("Create Sales Order with {0} won item(s)? You can edit quantity and rate in the Sales Order before submitting.", [won_count]),
					function() {
						frappe.call({
							method: "pepl_os.pepl_os.doctype.pepl_tender.pepl_tender.create_sales_order_from_tender",
							args: { tender_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Creating Sales Order..."),
							callback: function(r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Sales Order {0} created with {1} item(s)",
											[r.message.sales_order, r.message.items_added]),
										indicator: "green"
									});
									setTimeout(() => {
										frappe.set_route("Form", "Sales Order", r.message.sales_order);
									}, 1500);
								}
							}
						});
					}
				);
			}, __("Order")).addClass("btn-primary");
		}

		// If SO already linked — View Sales Order button + indicator
		if (frm.doc.linked_sales_order) {
			frm.add_custom_button(__("View Sales Order"), function() {
				frappe.set_route("Form", "Sales Order", frm.doc.linked_sales_order);
			}, __("Order"));

			frm.dashboard.add_indicator(
				__("Order Received: {0}", [frm.doc.linked_sales_order]),
				"purple"
			);
		}

		// Financial summary in dashboard
		if (!frm.is_new() && frm.doc.total_estimated_value) {
			const win_info = frm.doc.win_rate ? ` | Win Rate: ${frm.doc.win_rate.toFixed(1)}%` : "";
			const est = frappe.format(frm.doc.total_estimated_value, { fieldtype: "Currency" });
			const bid = frappe.format(frm.doc.total_bid_value || 0, { fieldtype: "Currency" });
			frm.dashboard.add_comment(
				`Est: \u20b9${est} | Bid: \u20b9${bid}${win_info}`,
				"blue",
				true
			);
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			frappe.db.get_value("Customer", frm.doc.customer, "customer_group", (r) => {
				if (r && r.customer_group) {
					frm.set_value("customer_group", r.customer_group);

					if (r.customer_group.includes("Railways")) {
						frm.set_value("sector", "Railways");
					} else if (r.customer_group.includes("Defence")) {
						frm.set_value("sector", "Defence");
					} else if (r.customer_group.includes("Private")) {
						frm.set_value("sector", "Private");
					}

					frm.set_value("sub_sector", r.customer_group);
				}
			});
		}
	},

	bid_securing_declaration(frm) {
		if (frm.doc.bid_securing_declaration) {
			frm.set_value("emd_required", 0);
		}
	},

	emd_required(frm) {
		if (frm.doc.emd_required) {
			frm.set_value("bid_securing_declaration", 0);
		}
	},

	customer_po_received(frm) {
		if (frm.doc.customer_po_received && !frm.doc.po_date) {
			frm.set_value("po_date", frappe.datetime.get_today());
		}
	}
});

frappe.ui.form.on("PEPL Tender Item", {
	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.quantity && row.estimated_unit_price) {
			frappe.model.set_value(cdt, cdn, "estimated_total_value",
				row.quantity * row.estimated_unit_price);
		}
		if (row.quantity && row.our_bid_unit_price) {
			frappe.model.set_value(cdt, cdn, "our_bid_total_value",
				row.quantity * row.our_bid_unit_price);
		}
	},

	estimated_unit_price(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.quantity && row.estimated_unit_price) {
			frappe.model.set_value(cdt, cdn, "estimated_total_value",
				row.quantity * row.estimated_unit_price);
		}
	},

	our_bid_unit_price(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.quantity && row.our_bid_unit_price) {
			frappe.model.set_value(cdt, cdn, "our_bid_total_value",
				row.quantity * row.our_bid_unit_price);
		}
	}
});
