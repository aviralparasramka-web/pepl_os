// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

frappe.ui.form.on('Request for Quotation', {
	refresh: function (frm) {
		if (!frappe.meta.get_docfield('Request for Quotation', 'per_item_vendor_selections')) {
			return;
		}

		var has_codes = (frm.doc.items || []).some(function (r) { return !!r.item_code; });

		if (
			frm.doc.docstatus === 0 &&
			has_codes &&
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

		if (
			frm.doc.docstatus === 1 &&
			(frm.doc.per_item_vendor_selections || []).length > 0
		) {
			pepl_rfq2_install_send_btn(frm);
		}
	}
});

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
		__('Send per-item RFQ emails to all selected vendors?'),
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
							lines.map(function (s) { return frappe.utils.escape_html(s); }).join('</li><li>') +
							'</li></ul>'
						);
					}
					if ((data.skipped || []).length) {
						frappe.msgprint({
							title: __('Vendors skipped — no email on record'),
							message: (data.skipped || []).map(function (s) {
								return frappe.utils.escape_html(s);
							}).join(', '),
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

function pepl_rfq2_h(s) {
	return frappe.utils.escape_html(String(s == null ? '' : s));
}

function pepl_rfq2_open(frm) {
	if (frm.is_dirty() || frm.doc.__islocal || !frm.doc.name) {
		frappe.msgprint(__('Save the RFQ before configuring vendors per item.'));
		return;
	}

	frappe.call({
		method: 'pepl_os.pepl_os.api.rfq_phase2.populate_per_item_vendors',
		args: { rfq_name: frm.doc.name },
		freeze: true,
		callback: function () {
			frappe.call({
				method: 'pepl_os.pepl_os.api.rfq_phase2.get_per_item_qualified_vendors',
				args: { rfq_name: frm.doc.name },
				freeze: true,
				callback: function (r2) {
					var items = (r2.message && r2.message.items) || [];
					if (!items.length) {
						frappe.msgprint(__('No RFQ items with Item Code found.'));
						return;
					}
					pepl_rfq2_build_dialog(frm, items);
				},
				error: function () {
					frappe.msgprint(__('Could not load qualified vendors for display.'));
				}
			});
		},
		error: function () {
			frappe.msgprint(__('Could not populate per-item vendors.'));
		}
	});
}

function pepl_rfq2_sel_lookup(frm, idx, ic, vendor) {
	var rows = frm.doc.per_item_vendor_selections || [];
	for (var i = 0; i < rows.length; i++) {
		var r = rows[i];
		if (
			String(r.rfq_item_idx) === String(idx) &&
			r.rfq_item_code === ic &&
			r.vendor === vendor &&
			cint(r.is_qualified) === 1
		) {
			return cint(r.is_selected) ? true : false;
		}
	}
	return true;
}

function pepl_rfq2_build_dialog(frm, items) {
	var html = '<p class="text-muted small">' +
		pepl_rfq2_h(__('One email per vendor. Each vendor receives only the items checked for them.')) +
		'</p>';

	items.forEach(function (bucket) {
		var idx = bucket.rfq_item_idx;
		var ic = bucket.item_code;

		var q_rows = '';
		(bucket.qualified_vendors || []).forEach(function (v) {
			var prior_sel = pepl_rfq2_sel_lookup(frm, idx, ic, v.vendor);
			var checked = (prior_sel !== false) ? 'checked' : '';
			q_rows +=
				'<tr>' +
				'<td style="width:40px;text-align:center">' +
				'<input type="checkbox" class="pepl-rfq2-qcb" ' + checked +
				' data-item-idx="' + pepl_rfq2_h(idx) + '"' +
				' data-item-code="' + pepl_rfq2_h(ic) + '"' +
				' data-vendor="' + pepl_rfq2_h(v.vendor) + '"' +
				' data-source="' + pepl_rfq2_h(v.source || '') + '"' +
				' /></td>' +
				'<td>' + pepl_rfq2_h(v.vendor_name || v.vendor) + '</td>' +
				'<td>' + pepl_rfq2_h(v.source || '') + '</td>' +
				'</tr>';
		});

		var m_rows = '';
		(frm.doc.per_item_vendor_selections || []).forEach(function (r) {
			if (String(r.rfq_item_idx) !== String(idx)) return;
			if (r.rfq_item_code !== ic) return;
			if (cint(r.is_qualified) !== 0) return;
			var checked_m = cint(r.is_selected) ? 'checked' : '';
			var vesc = pepl_rfq2_h(r.vendor);
			m_rows +=
				'<tr>' +
				'<td style="width:40px;text-align:center">' +
				'<input type="checkbox" class="pepl-rfq2-mcb" ' + checked_m +
				' data-item-idx="' + pepl_rfq2_h(idx) + '"' +
				' data-item-code="' + pepl_rfq2_h(ic) + '"' +
				' data-vendor="' + vesc + '"' +
				' /></td>' +
				'<td>' + vesc + ' <span class="badge badge-warning">M</span></td>' +
				'</tr>';
		});

		var m_vis = m_rows ? '' : 'display:none;';

		html += '<div class="pepl-rfq2-block"' +
			' data-item-idx="' + pepl_rfq2_h(idx) + '"' +
			' data-item-code="' + pepl_rfq2_h(ic) + '"' +
			' style="margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #eee">';

		html += '<h6 style="margin:8px 0 4px">' +
			pepl_rfq2_h(ic) + ' &mdash; ' + pepl_rfq2_h(bucket.item_name) +
			'</h6>';

		html += '<div class="text-muted small">' + pepl_rfq2_h(__('Qualified vendors')) + '</div>';
		html +=
			'<table class="table table-bordered table-condensed" style="margin-bottom:6px">' +
			'<thead><tr>' +
			'<th style="width:40px"></th>' +
			'<th>' + pepl_rfq2_h(__('Vendor')) + '</th>' +
			'<th>' + pepl_rfq2_h(__('Source')) + '</th>' +
			'</tr></thead><tbody>' +
			(q_rows || '<tr><td colspan="3"><i class="text-muted">' + pepl_rfq2_h(__('None found')) + '</i></td></tr>') +
			'</tbody></table>';

		html += '<div class="text-muted small">' + pepl_rfq2_h(__('Manual vendors')) + '</div>';
		html +=
			'<table class="table table-bordered table-condensed pepl-rfq2-manual"' +
			' style="margin-bottom:6px;' + m_vis + '">' +
			'<tbody>' + m_rows + '</tbody></table>';
		html +=
			'<button type="button" class="btn btn-xs btn-secondary pepl-rfq2-manual-add">' +
			pepl_rfq2_h(__('Add Manual Vendor')) +
			'</button>';

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

	dlg.$wrapper.on('click', '.pepl-rfq2-manual-add', function () {
		var block = $(this).closest('.pepl-rfq2-block');
		var tbl = block.find('.pepl-rfq2-manual');
		frappe.prompt(
			[{
				fieldtype: 'Link',
				options: 'Supplier',
				fieldname: 'supplier',
				label: __('Supplier'),
				reqd: 1
			}],
			function (vals) {
				var vesc = frappe.utils.escape_html(vals.supplier);
				tbl.show();
				tbl.find('tbody').append(
					'<tr>' +
					'<td style="width:40px;text-align:center">' +
					'<input type="checkbox" class="pepl-rfq2-mcb" checked' +
					' data-item-idx="' + frappe.utils.escape_html(block.attr('data-item-idx')) + '"' +
					' data-item-code="' + frappe.utils.escape_html(block.attr('data-item-code')) + '"' +
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

function pepl_rfq2_apply(frm, dlg) {
	frappe.model.clear_table(frm.doc, 'per_item_vendor_selections');

	var seen = {};

	function add_sel(rfq_item_idx, rfq_item_code, vendor, is_qualified, source) {
		var key = rfq_item_idx + '||' + rfq_item_code + '||' + vendor;
		if (seen[key]) return;
		seen[key] = 1;
		var row = frappe.model.add_child(frm.doc, 'per_item_vendor_selections');
		row.rfq_item_idx = cint(rfq_item_idx);
		row.rfq_item_code = rfq_item_code;
		row.vendor = vendor;
		row.is_qualified = is_qualified;
		row.source = source || '';
		row.is_selected = 1;
	}

	dlg.$wrapper.find('.pepl-rfq2-qcb:checked').each(function () {
		var el = $(this);
		add_sel(
			el.attr('data-item-idx'),
			el.attr('data-item-code'),
			el.attr('data-vendor'),
			1,
			el.attr('data-source') || ''
		);
	});

	dlg.$wrapper.find('.pepl-rfq2-mcb:checked').each(function () {
		var el = $(this);
		add_sel(
			el.attr('data-item-idx'),
			el.attr('data-item-code'),
			el.attr('data-vendor'),
			0,
			'Manual Override'
		);
	});

	dlg.hide();
	frm.refresh_field('per_item_vendor_selections');
	frm.save().then(function () {
		frappe.show_alert({ message: __('Per-item vendor selections saved.'), indicator: 'green' });
	});
}
