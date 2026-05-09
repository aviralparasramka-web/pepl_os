// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
//
// RFQ Phase 2 — per-item target_vendors (Table MultiSelect on RFQ Item).
// Guard: checks for target_vendors field on "Request for Quotation Item".

frappe.ui.form.on('Request for Quotation', {
	refresh: function (frm) {
		if (!frappe.meta.get_docfield('Request for Quotation Item', 'target_vendors')) {
			return;
		}

		var has_items = (frm.doc.items || []).some(function (r) { return !!r.item_code; });

		// "Configure Vendors per Item" button — available on saved, clean draft
		if (
			frm.doc.docstatus === 0 &&
			has_items &&
			!frm.doc.__islocal &&
			frm.doc.name &&
			!frm.is_dirty()
		) {
			frm.remove_custom_button(__('Configure Vendors per Item'), __('Actions'));
			frm.add_custom_button(
				__('Configure Vendors per Item'),
				function () { pepl_rfq2_open(frm); },
				__('Actions')
			);
		}

		// "Send RFQ to Vendors" button — replaces standard send on submitted docs
		// that have any target_vendors configured
		if (frm.doc.docstatus === 1 && pepl_rfq2_has_selections(frm)) {
			pepl_rfq2_install_send_btn(frm);
		}
	}
});

// ── Helpers ────────────────────────────────────────────────────────────────

function pepl_rfq2_h(s) {
	return frappe.utils.escape_html(String(s == null ? '' : s));
}

function pepl_rfq2_has_selections(frm) {
	return (frm.doc.items || []).some(function (it) {
		return it.item_code && (it.target_vendors || []).length > 0;
	});
}

// ── Send button ────────────────────────────────────────────────────────────

function pepl_rfq2_install_send_btn(frm) {
	frappe.after_ajax(function () {
		setTimeout(function () {
			try { frm.page.remove_inner_button(__('Send Emails to Suppliers'), __('Tools')); } catch (e) {}
			try { frm.remove_custom_button(__('Send Emails to Suppliers'), __('Tools')); } catch (e) {}
			frm.add_custom_button(
				__('Send RFQ to Vendors'),
				function () { pepl_rfq2_send(frm); },
				__('Tools')
			);
		}, 300);
	});
}

function pepl_rfq2_send(frm) {
	frappe.confirm(
		__('Send per-item RFQ emails to all target vendors?'),
		function () {
			frappe.call({
				method: 'pepl_os.pepl_os.api.rfq_phase2.send_rfq_emails_phase2',
				args: { rfq_name: frm.doc.name },
				freeze: true,
				callback: function (r) {
					var data = r.message || {};
					var lines = data.summaries || [];
					if (lines.length) {
						frappe.msgprint(
							'<ul style="margin-left:14px"><li>' +
							lines.map(function (s) { return pepl_rfq2_h(s); }).join('</li><li>') +
							'</li></ul>'
						);
					}
					if ((data.skipped || []).length) {
						frappe.msgprint({
							title: __('Vendors skipped — no email on record'),
							message: data.skipped.map(pepl_rfq2_h).join(', '),
							indicator: 'orange'
						});
					}
					frm.reload_doc();
				},
				error: function () {
					frappe.msgprint(__('Unable to send emails. Check server logs.'));
				}
			});
		}
	);
}

// ── Dialog open ────────────────────────────────────────────────────────────

function pepl_rfq2_open(frm) {
	if (frm.is_dirty() || frm.doc.__islocal || !frm.doc.name) {
		frappe.msgprint(__('Save the RFQ before configuring vendors per item.'));
		return;
	}

	frappe.call({
		method: 'pepl_os.pepl_os.api.rfq_phase2.get_qualified_vendors_per_item',
		args: { rfq_name: frm.doc.name },
		freeze: true,
		callback: function (r) {
			var items = (r.message && r.message.items) || [];
			if (!items.length) {
				frappe.msgprint(__('No RFQ items with Item Code found.'));
				return;
			}
			pepl_rfq2_build_dialog(frm, items);
		},
		error: function () {
			frappe.msgprint(__('Could not load qualified vendors.'));
		}
	});
}

// ── Dialog builder ─────────────────────────────────────────────────────────

function pepl_rfq2_build_dialog(frm, items) {
	var html = '<p class="text-muted small">' +
		pepl_rfq2_h(__('One email per vendor. Each vendor receives only the items it is checked for.')) +
		'</p>';

	items.forEach(function (bucket) {
		var item_idx = bucket.rfq_item_idx;
		var ic = bucket.item_code;

		// Build a set of all tier suppliers so manual rows can exclude them
		var tier_suppliers = {};
		function note_tier(list, tier) {
			(list || []).forEach(function (v) { if (v.supplier) tier_suppliers[v.supplier] = tier; });
		}
		note_tier(bucket.tier1, 1);
		note_tier(bucket.tier2, 2);
		note_tier(bucket.tier3, 3);

		var current = {};
		(bucket.current_vendors || []).forEach(function (s) { current[s] = true; });

		// Tier-1 rows (Approved — specific item): checked by default or if in current
		var t1_rows = pepl_rfq2_vendor_rows(
			bucket.tier1 || [], item_idx, ic, current, true,
			'pepl-rfq2-t1cb', 'success', __('Tier 1 — Approved (Item)')
		);

		// Tier-2 rows (Approved — RM group): unchecked by default unless in current
		var t2_rows = pepl_rfq2_vendor_rows(
			bucket.tier2 || [], item_idx, ic, current, false,
			'pepl-rfq2-t2cb', 'info', __('Tier 2 — Approved (RM Group)')
		);

		// Tier-3 rows (PO history, no formal approval): unchecked by default
		var t3_rows = pepl_rfq2_vendor_rows(
			bucket.tier3 || [], item_idx, ic, current, false,
			'pepl-rfq2-t3cb', 'warning', __('Tier 3 — PO History')
		);

		// Manual rows: current_vendors that are NOT in any tier
		var manual_html = '';
		(bucket.current_vendors || []).forEach(function (sup) {
			if (tier_suppliers[sup]) return; // Already shown in a tier table
			var vesc = pepl_rfq2_h(sup);
			manual_html +=
				'<tr>' +
				'<td style="width:40px;text-align:center">' +
				'<input type="checkbox" class="pepl-rfq2-mcb" checked' +
				' data-item-idx="' + pepl_rfq2_h(item_idx) + '"' +
				' data-item-code="' + pepl_rfq2_h(ic) + '"' +
				' data-vendor="' + vesc + '" /></td>' +
				'<td>' + vesc + ' <span class="badge badge-warning">M</span></td>' +
				'</tr>';
		});
		var manual_vis = manual_html ? '' : 'display:none;';

		html += '<div class="pepl-rfq2-block"' +
			' data-item-idx="' + pepl_rfq2_h(item_idx) + '"' +
			' data-item-code="' + pepl_rfq2_h(ic) + '"' +
			' style="margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #eee">';

		html += '<h6 style="margin:8px 0 6px">' +
			pepl_rfq2_h(ic) + ' &mdash; ' + pepl_rfq2_h(bucket.item_name) + '</h6>';

		// Tier 1
		if (t1_rows) {
			html += pepl_rfq2_tier_table(t1_rows, __('Tier 1 — Approved (Item History)'));
		}
		// Tier 2
		if (t2_rows) {
			html += pepl_rfq2_tier_table(t2_rows, __('Tier 2 — Approved (RM Group)'));
		}
		// Tier 3
		if (t3_rows) {
			html += pepl_rfq2_tier_table(t3_rows, __('Tier 3 — PO History (not formally approved)'));
		}
		if (!t1_rows && !t2_rows && !t3_rows) {
			html += '<p class="text-muted small"><i>' + pepl_rfq2_h(__('No qualified vendors found from 3-tier lookup.')) + '</i></p>';
		}

		// Manual
		html += '<div class="text-muted small" style="margin-top:4px">' + pepl_rfq2_h(__('Manual vendors')) + '</div>';
		html +=
			'<table class="table table-bordered table-condensed pepl-rfq2-manual"' +
			' style="margin-bottom:4px;' + manual_vis + '">' +
			'<tbody>' + manual_html + '</tbody></table>';
		html += '<button type="button" class="btn btn-xs btn-default pepl-rfq2-manual-add">' +
			pepl_rfq2_h(__('Add Manual Vendor')) + '</button>';

		html += '</div>';
	});

	var dlg = new frappe.ui.Dialog({
		title: __('Configure vendors per item'),
		size: 'large',
		fields: [{ fieldtype: 'HTML', fieldname: 'body', options: html }],
		primary_action_label: __('Apply'),
		primary_action: function () {
			pepl_rfq2_apply(frm, dlg);
		}
	});

	// ONE delegated handler for the manual-add button
	dlg.$wrapper.on('click', '.pepl-rfq2-manual-add', function () {
		var block = $(this).closest('.pepl-rfq2-block');
		var tbl = block.find('.pepl-rfq2-manual');
		frappe.prompt(
			[{ fieldtype: 'Link', options: 'Supplier', fieldname: 'supplier', label: __('Supplier'), reqd: 1 }],
			function (vals) {
				var vesc = pepl_rfq2_h(vals.supplier);
				tbl.show();
				tbl.find('tbody').append(
					'<tr>' +
					'<td style="width:40px;text-align:center">' +
					'<input type="checkbox" class="pepl-rfq2-mcb" checked' +
					' data-item-idx="' + pepl_rfq2_h(block.attr('data-item-idx')) + '"' +
					' data-item-code="' + pepl_rfq2_h(block.attr('data-item-code')) + '"' +
					' data-vendor="' + vesc + '" /></td>' +
					'<td>' + vesc + ' <span class="badge badge-warning">M</span></td>' +
					'</tr>'
				);
			},
			__('Add manual supplier')
		);
	});

	dlg.show();
}

function pepl_rfq2_tier_table(rows_html, label) {
	return '<div class="text-muted small" style="margin-top:4px">' + pepl_rfq2_h(label) + '</div>' +
		'<table class="table table-bordered table-condensed" style="margin-bottom:4px">' +
		'<thead><tr>' +
		'<th style="width:40px"></th>' +
		'<th>' + pepl_rfq2_h(__('Vendor')) + '</th>' +
		'<th>' + pepl_rfq2_h(__('Source')) + '</th>' +
		'</tr></thead><tbody>' + rows_html + '</tbody></table>';
}

function pepl_rfq2_vendor_rows(list, item_idx, ic, current, default_checked, cbClass, badge, badge_label) {
	if (!list.length) return '';
	var out = '';
	list.forEach(function (v) {
		var sup = v.supplier;
		if (!sup) return;
		var is_checked = (sup in current) ? current[sup] : default_checked;
		var checked = is_checked ? 'checked' : '';
		out +=
			'<tr>' +
			'<td style="width:40px;text-align:center">' +
			'<input type="checkbox" class="' + cbClass + '" ' + checked +
			' data-item-idx="' + pepl_rfq2_h(item_idx) + '"' +
			' data-item-code="' + pepl_rfq2_h(ic) + '"' +
			' data-vendor="' + pepl_rfq2_h(sup) + '"' +
			' /></td>' +
			'<td>' + pepl_rfq2_h(v.supplier_name || sup) + '</td>' +
			'<td>' + pepl_rfq2_h(v.source_label || '') + '</td>' +
			'</tr>';
	});
	return out;
}

// ── Apply ──────────────────────────────────────────────────────────────────

function pepl_rfq2_apply(frm, dlg) {
	// Build a map: item_idx → [supplier, ...]
	var vendor_map = {};

	function note(idx, vendor) {
		if (!idx || !vendor) return;
		var key = String(idx);
		if (!vendor_map[key]) vendor_map[key] = {};
		vendor_map[key][vendor] = true;
	}

	// Collect all checked boxes (tier 1, 2, 3, manual)
	dlg.$wrapper.find(
		'.pepl-rfq2-t1cb:checked, .pepl-rfq2-t2cb:checked, ' +
		'.pepl-rfq2-t3cb:checked, .pepl-rfq2-mcb:checked'
	).each(function () {
		var el = $(this);
		note(el.attr('data-item-idx'), el.attr('data-vendor'));
	});

	// Write to each item's target_vendors child table
	(frm.doc.items || []).forEach(function (it) {
		if (!it.item_code) return;
		var key = String(it.idx);
		var vendors = vendor_map[key] ? Object.keys(vendor_map[key]) : [];

		// Clear existing target_vendors rows for this item
		frappe.model.clear_table(it, 'target_vendors');

		vendors.forEach(function (sup) {
			var row = frappe.model.add_child(it, 'PEPL RFQ Item Target Vendor', 'target_vendors');
			row.supplier = sup;
		});
	});

	dlg.hide();
	frm.refresh_field('items');
	frm.save().then(function () {
		frappe.show_alert({ message: __('Per-item vendor selections saved.'), indicator: 'green' });
	});
}
