// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

frappe.ui.form.on('Request for Quotation', {
	refresh(frm) {
		if (frm.fields_dict.suppliers) {
			frm.set_query('supplier', 'suppliers', function () {
				return {
					query: 'pepl_os.pepl_os.api.purchase_queries.supplier_list_query_for_rfq',
				};
			});
		}
		if (!frm.is_new()) {
			frm.add_custom_button(
				__('Auto-fill Qualified Vendors'),
				() => pepl_rfq_autofill_qualified_vendors(frm),
				__('Actions')
			);
		}
	},
});

function pepl_rfq_autofill_qualified_vendors(frm) {
	const codes = [];
	for (const row of frm.doc.items || []) {
		if (row.item_code && codes.indexOf(row.item_code) === -1) {
			codes.push(row.item_code);
		}
	}
	if (!codes.length) {
		frappe.msgprint({
			title: __('Qualified vendors'),
			message: __('Add RFQ items first.'),
			indicator: 'orange',
		});
		return;
	}

	const merged = {};
	function ingest(list) {
		for (const s of list || []) {
			const sup = s.supplier;
			if (!sup) continue;
			const rank =
				s.source === 'approved_specific_item'
					? 1
					: s.source === 'approved_rm_group'
						? 2
						: 3;
			const prev = merged[sup];
			if (!prev || rank < prev._rank) {
				merged[sup] = Object.assign({ _rank: rank }, s);
			}
		}
	}

	let chain = Promise.resolve();
	for (const ic of codes) {
		chain = chain.then(() => {
			return frappe.call({
				method: 'pepl_os.pepl_os.api.cst_intelligence.get_qualified_vendors_for_item',
				args: { item_code: ic, lookback_months: 18 },
			});
		}).then((r) => {
			const msg = r.message || {};
			ingest(msg.suppliers || []);
		});
	}

	chain
		.then(() => {
			const suppliers = Object.keys(merged).map((k) => {
				const row = merged[k];
				delete row._rank;
				return row;
			});
			if (!suppliers.length) {
				frappe.msgprint(__('No qualified vendors aggregated from RFQ items.'));
				return;
			}
			let html = '';
			for (const s of suppliers) {
				let lbl = '';
				if (s.source === 'approved_specific_item') {
					lbl = __('Approved (specific item)');
				} else if (s.source === 'approved_rm_group') {
					lbl = __('Approved (via RM Group)');
				} else {
					lbl = __('Past supplier (no formal approval yet)');
				}
				html +=
					'<div class="checkbox"><label>' +
					'<input type="checkbox" class="pepl-rfq-pick" data-supplier="' +
					frappe.utils.escape_html(s.supplier) +
					'" checked /> ' +
					frappe.utils.escape_html(s.supplier_name || s.supplier) +
					' <span class="text-muted small">(' +
					lbl +
					')</span></label></div>';
			}
			const d = new frappe.ui.Dialog({
				title: __('Select vendors to add'),
				fields: [
					{
						fieldtype: 'HTML',
						fieldname: 'vendors_html',
						options:
							'<p class="text-muted small">' +
							__('Uncheck vendors you do not want on this RFQ.') +
							'</p>' +
							html,
					},
				],
				primary_action_label: __('Add to RFQ'),
				primary_action() {
					const chosen = [];
					d.$wrapper.find('.pepl-rfq-pick:checked').each(function () {
						chosen.push($(this).attr('data-supplier'));
					});
					d.hide();
					const existing = new Set((frm.doc.suppliers || []).map((r) => r.supplier));
					for (const sup of chosen) {
						if (existing.has(sup)) continue;
						const row = frm.add_child('suppliers');
						row.supplier = sup;
						existing.add(sup);
					}
					frm.refresh_field('suppliers');
					frappe.show_alert({
						message: __('Updated RFQ supplier rows'),
						indicator: 'green',
					});
				},
			});
			d.show();
		})
		.catch(() => {
			frappe.msgprint(__('Could not load qualified vendors.'));
		});
}
