// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

frappe.ui.form.on('PEPL CST Cost Sheet', {
	refresh(frm) {
		frm.remove_custom_button(__('Import from BOM'), __('CST Intelligence'));
		if (!frm.is_new() && frm.doc.linked_item) {
			frm.add_custom_button(
				__('Import from BOM'),
				() => pepl_import_bom_components(frm),
				__('CST Intelligence')
			);
		}
		frm.remove_custom_button(__('Rate Reference (selected row)'), __('CST Intelligence'));
		frm.add_custom_button(
			__('Rate Reference (selected row)'),
			() => pepl_open_rate_ref_selected_row(frm),
			__('CST Intelligence')
		);

		frm.remove_custom_button(__('Quotation'), __('Create'));
		if (!frm.is_new()) {
			frm.add_custom_button(
				__('Quotation'),
				() => pepl_create_quotation_from_cst(frm),
				__('Create')
			);
		}
	},
});

function pepl_cst_component_row_has_cost(row) {
	if (!row) return false;
	if (flt(row.component_subtotal) > 0) return true;
	return (
		flt(row.raw_material_cost) +
			flt(row.machining_cost) +
			flt(row.surface_treatment_cost) +
			flt(row.bought_out_cost) +
			flt(row.component_other_charges) >
		0
	);
}

function pepl_cst_has_component_with_cost(doc) {
	const rows = doc.components || [];
	if (!rows.length) return false;
	return rows.some((r) => pepl_cst_component_row_has_cost(r));
}

function pepl_call_create_quotation_from_cst(frm, override_customer) {
	frappe.call({
		method: 'pepl_os.pepl_os.api.cst_intelligence.create_quotation_from_cst',
		args: {
			cst_name: frm.doc.name,
			override_customer: override_customer || null,
		},
		freeze: true,
		callback(r) {
			if (r.exc) {
				return;
			}
			const qname = r.message && r.message.name;
			if (!qname) return;
			frappe.show_alert({
				message: __('Quotation {0} created', [qname]),
				indicator: 'green',
			});
			frappe.confirm(
				__('Send to customer now?'),
				function () {
					frappe.call({
						method: 'pepl_os.pepl_os.api.cst_intelligence.get_quotation_email_context',
						args: { quotation_name: qname },
						callback(res) {
							const ctx = res.message || {};
							if (!ctx.recipients) {
								frappe.msgprint({
									title: __('Email'),
									message: __(
										'No customer email on quotation or customer record — add email, then send manually.'
									),
									indicator: 'orange',
								});
							}
							if (frappe.views && frappe.views.CommunicationComposer) {
								try {
									new frappe.views.CommunicationComposer({
										doc: {
											doctype: 'Quotation',
											name: qname,
										},
										subject: ctx.subject || '',
										recipients: ctx.recipients || '',
										content: ctx.message || '',
										message: ctx.message || '',
										attach_document_print: true,
									});
								} catch (e) {
									frappe.msgprint(
										__('Open Quotation {0} and use Menu → Email to send.', [qname])
									);
								}
							}
						},
					});
				},
				function () {
					/* user sends later from Quotation */
				}
			);
		},
		error(r) {
			const msg =
				(r && r.message) ||
				__('Could not create quotation. Check messages and try again.');
			frappe.msgprint({ title: __('Quotation'), message: msg, indicator: 'red' });
		},
	});
}

function pepl_prompt_customer_for_quotation(frm, proceed) {
	const d = new frappe.ui.Dialog({
		title: __('Customer required'),
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'hint',
				options:
					'<p class="text-muted small">' +
					__(
						'This Cost Sheet has no Customer and Linked Product has no Primary Customer. Pick a Customer for the quotation.'
					) +
					'</p>',
			},
			{
				fieldname: 'customer',
				label: __('Customer'),
				fieldtype: 'Link',
				options: 'Customer',
				reqd: 1,
			},
		],
		primary_action_label: __('Create quotation'),
		primary_action(values) {
			const c = values.customer;
			if (!c) {
				frappe.msgprint({ title: __('Customer'), message: __('Select a customer.'), indicator: 'orange' });
				return;
			}
			d.hide();
			proceed(c);
		},
	});
	d.show();
}

function pepl_create_quotation_from_cst(frm) {
	if (frm.is_new()) {
		frappe.msgprint({
			title: __('Quotation'),
			message: __('Save the Cost Sheet first.'),
			indicator: 'orange',
		});
		return;
	}
	if (!frm.doc.linked_product) {
		frappe.msgprint({
			title: __('Quotation'),
			message: __('Set Linked Product first.'),
			indicator: 'red',
		});
		return;
	}
	if (!frm.doc.linked_item) {
		frappe.msgprint({
			title: __('Quotation'),
			message: __('Linked Item is missing. Set Linked Product so Item is fetched.'),
			indicator: 'red',
		});
		return;
	}
	if (!pepl_cst_has_component_with_cost(frm.doc)) {
		frappe.msgprint({
			title: __('Quotation'),
			message: __(
				'Add at least one component line with cost (subtotal or cost fields) before creating a quotation.'
			),
			indicator: 'orange',
		});
		return;
	}

	const run = (override_customer) => pepl_call_create_quotation_from_cst(frm, override_customer);

	if (frm.doc.customer) {
		run(null);
		return;
	}

	frappe.db.get_value('PEPL Product Master', frm.doc.linked_product, 'primary_customer').then((r) => {
		const fallback = r && r.message && r.message.primary_customer;
		if (fallback) {
			run(null);
			return;
		}
		pepl_prompt_customer_for_quotation(frm, (cust) => run(cust));
	});
}

function pepl_import_bom_components(frm) {
	frappe.call({
		method: 'pepl_os.pepl_os.api.cst_intelligence.import_components_from_bom',
		args: { cst_name: frm.doc.name },
		callback(r) {
			const msg = r.message || {};
			if (msg.error) {
				frappe.msgprint({ title: __('BOM import'), message: msg.error, indicator: 'red' });
				return;
			}
			const comps = msg.components || [];
			if (!comps.length) {
				frappe.msgprint(__('No stock BOM lines found.'));
				return;
			}
			const bomLabel = msg.bom_name || '';
			frappe.confirm(
				__(
					'Import {0} components from BOM {1}? This will append to existing components.',
					[comps.length, bomLabel]
				),
				() => {
					let imported = 0;
					for (const c of comps) {
						const r = frm.add_child('components', {
							manufactured_or_bought_out: c.manufactured_or_bought_out || 'Manufactured',
							component_item: c.component_item,
							rm_group: c.rm_group,
							quantity_per_assembly: c.quantity_per_assembly,
							uom: c.uom,
							component_drawing_no: c.component_drawing_no || '',
						});
						imported += 1;
						if (typeof calculate_subtotal === 'function') {
							calculate_subtotal(frm, 'PEPL CST Component', r.name);
						}
					}
					frm.refresh_field('components');
					const totalImported =
						msg.total_imported != null ? msg.total_imported : imported;
					frappe.show_alert({
						message: __('Imported {0} components', [totalImported]),
						indicator: 'green',
					});
					const unmappedCount =
						msg.unmapped_count != null ? msg.unmapped_count : 0;
					const unmappedItems = msg.unmapped_items || [];
					if (unmappedCount > 0) {
						let body =
							'<p>' +
							__('The following components need manual RM Group classification:') +
							'</p>';
						if (unmappedItems.length) {
							body += '<ul>';
							for (const u of unmappedItems) {
								body +=
									'<li>' +
									frappe.utils.escape_html(
										u.item_name || u.component_item || ''
									) +
									'</li>';
							}
							body += '</ul>';
						} else {
							body +=
								'<p>' +
								__('({0} item(s))', [unmappedCount]) +
								'</p>';
						}
						body +=
							'<p>' +
							__(
								'Please review the imported components and set the correct RM Group before saving.'
							) +
							'</p>';
						frappe.msgprint({
							title: __('RM Group Classification Needed'),
							message: body,
							indicator: 'orange',
						});
					}
				},
				() => {}
			);
		},
	});
}

function pepl_open_rate_ref_selected_row(frm) {
	const grid = frm.fields_dict.components && frm.fields_dict.components.grid;
	if (!grid) return;
	const doc = grid.get_selected_children()[0];
	if (!doc) {
		frappe.msgprint(__('Select a component row first.'));
		return;
	}
	const cdn = doc.name;
	pepl_open_rate_reference_dialog(frm, 'PEPL CST Component', cdn);
}

function pepl_open_rate_reference_dialog(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || !row.component_item) {
		frappe.msgprint(__('Set Item on the row first.'));
		return;
	}

	frappe.call({
		method: 'pepl_os.pepl_os.api.cst_intelligence.get_rate_references',
		args: { item_code: row.component_item },
		callback(r) {
			const refs = (r.message && r.message.references) || [];
			const mo = row.manufactured_or_bought_out || 'Manufactured';
			const qpa = flt(row.quantity_per_assembly) || 1;
			const avail = refs.filter((x) => x.available);
			let defaultManual = 0;
			if (mo === 'Bought Out') {
				defaultManual = qpa ? flt(row.bought_out_cost) / qpa : 0;
			} else {
				defaultManual = qpa ? flt(row.raw_material_cost) / qpa : 0;
			}
			if (!defaultManual && avail.length && avail[0].rate != null) {
				defaultManual = flt(avail[0].rate);
			}

			const dialog = new frappe.ui.Dialog({
				title: __('Rate Reference for {0}', [row.component_item]),
				fields: [
					{
						fieldname: 'hint',
						fieldtype: 'HTML',
						options:
							'<p class="text-muted small">' +
							__(
								'Enter PER-UNIT rate. Server will multiply by this row\'s quantity_per_assembly and write to raw_material_cost or bought_out_cost based on the row\'s classification. Document will save and refresh.'
							) +
							'</p>' +
							pepl_build_refs_table_html(refs),
					},
					{
						fieldname: 'manual_rate',
						label: __('Manual Rate (per unit)'),
						fieldtype: 'Currency',
						default: defaultManual,
					},
				],
				primary_action_label: __('Apply'),
				primary_action(values) {
					const manual_rate = flt(
						values && values.manual_rate != null ? values.manual_rate : dialog.get_value('manual_rate')
					);
					if (!manual_rate || manual_rate <= 0) {
						frappe.msgprint(__('Please enter a valid Manual Rate'));
						return;
					}

					const row_idx = locals[cdt][cdn].idx;
					if (!row_idx) {
						frappe.msgprint({
							title: __('Rate Reference'),
							message: __('Save the Cost Sheet first so component rows have a stable position.'),
							indicator: 'orange',
						});
						return;
					}

					const save_promise = frm.is_dirty() ? frm.save() : Promise.resolve();

					save_promise
						.then(() => {
							return frappe.call({
								method: 'pepl_os.pepl_os.api.cst_intelligence.apply_manual_rate',
								args: {
									cst_name: frm.doc.name,
									row_idx: row_idx,
									manual_rate: manual_rate,
								},
								freeze: true,
								freeze_message: __('Applying rate...'),
							});
						})
						.then((r) => {
							if (r && r.message && r.message.success) {
								const msg = r.message;
								frappe.show_alert({
									message: __('Wrote ₹{0} to {1} ({2} × {3})', [
										msg.computed_amount.toFixed(2),
										msg.target_field,
										msg.manual_rate,
										msg.qty_per_assembly,
									]),
									indicator: 'green',
								});
								dialog.hide();
								return frm.reload_doc();
							}
						})
						.catch((err) => {
							frappe.msgprint({
								title: __('Could not apply rate'),
								message: err.message || JSON.stringify(err),
								indicator: 'red',
							});
						});
				},
			});

			dialog.add_custom_action(__('Request Fresh Quote from Vendor'), () => {
				dialog.hide();
				pepl_open_vendor_rfq_dialog(frm, row.component_item, qpa);
			});

			dialog.show();
		},
	});
}

function pepl_build_refs_table_html(refs) {
	const rows = refs.filter((x) => x.available);
	if (!rows.length) {
		return '<p class="text-muted">' + __('No automated references available.') + '</p>';
	}
	let h =
		'<div class="table-responsive"><table class="table table-bordered table-condensed" style="font-size:12px;">';
	h +=
		'<thead><tr><th>Rank</th><th>Source</th><th>Rate</th><th>Age (days)</th><th>Reference</th></tr></thead><tbody>';
	for (const x of rows) {
		h +=
			'<tr><td>' +
			frappe.utils.escape_html(String(x.rank)) +
			'</td><td>' +
			frappe.utils.escape_html(x.source || '') +
			'</td><td>' +
			frappe.utils.escape_html(String(x.rate != null ? x.rate : '')) +
			'</td><td>' +
			frappe.utils.escape_html(String(x.age_days != null ? x.age_days : '—')) +
			'</td><td>' +
			frappe.utils.escape_html(x.reference_doc || '') +
			'</td></tr>';
	}
	h += '</tbody></table></div>';
	return h;
}

function pepl_open_vendor_rfq_dialog(frm, item_code, defaultQty) {
	if (frm.is_new()) {
		frappe.msgprint(__('Save the CST before emailing vendors.'));
		return;
	}
	frappe.call({
		method: 'pepl_os.pepl_os.api.cst_intelligence.get_qualified_vendors_for_item',
		args: { item_code, lookback_months: 18 },
		callback(r) {
			const suppliers = (r.message && r.message.suppliers) || [];
			if (!suppliers.length) {
				frappe.msgprint(
					__(
						'No qualified vendors found (approved RM coverage or PO history) for this item.'
					)
				);
				return;
			}
			let checksHtml = '';
			for (const s of suppliers) {
				let sourceLine = '';
				let srcClass = 'text-muted small';
				if (s.source === 'approved_specific_item') {
					sourceLine =
						' <span class="small text-success">(' + __('Approved (specific item)') + ')</span>';
					srcClass = 'small text-success';
				} else if (s.source === 'approved_rm_group') {
					const rg = s.rm_group ? frappe.utils.escape_html(String(s.rm_group)) : '—';
					sourceLine =
						' <span class="small text-success">(' +
						__('Approved (via RM Group {0})', [rg]) +
						')</span>';
					srcClass = 'small text-success';
				} else if (s.source === 'po_history') {
					sourceLine =
						' <span class="small text-warning">(' + __('Past supplier (no formal approval yet)') + ')</span>';
					srcClass = 'small text-warning';
				}
				checksHtml +=
					'<div class="checkbox"><label>' +
					'<input type="checkbox" class="pepl-rfq-supplier" data-supplier="' +
					frappe.utils.escape_html(s.supplier) +
					'" /> ' +
					frappe.utils.escape_html(s.supplier_name || s.supplier) +
					sourceLine +
					'<br/><span class="' +
					srcClass +
					'">' +
					__('Last PO') +
					': ' +
					frappe.utils.escape_html(s.last_po_date || '—') +
					', ' +
					__('Rate') +
					': ' +
					frappe.utils.escape_html(String(s.last_rate != null ? s.last_rate : '—')) +
					(s.approval_status
						? ' · ' +
						  __('Approval') +
						  ': ' +
						  frappe.utils.escape_html(String(s.approval_status))
						: '') +
					'</span></label></div>';
			}

			const d2 = new frappe.ui.Dialog({
				title: __('Request quote from vendors'),
				fields: [
					{
						fieldname: 'vendor_html',
						fieldtype: 'HTML',
						options:
							'<p class="text-muted small">' +
							__('Select vendors to email.') +
							'</p>' +
							checksHtml,
					},
					{
						fieldname: 'qty',
						label: __('Quantity'),
						fieldtype: 'Float',
						default: defaultQty || 1,
					},
					{
						fieldname: 'required_by',
						label: __('Required by'),
						fieldtype: 'Date',
					},
				],
				primary_action_label: __('Send emails'),
				primary_action() {
					const chosen = [];
					d2.$wrapper.find('.pepl-rfq-supplier:checked').each(function () {
						chosen.push($(this).attr('data-supplier'));
					});
					if (!chosen.length) {
						frappe.msgprint(__('Select at least one supplier.'));
						return;
					}
					frappe.call({
						method: 'pepl_os.pepl_os.api.cst_intelligence.send_rfq_email_to_suppliers',
						args: {
							item_code,
							supplier_list: JSON.stringify(chosen),
							qty: d2.get_value('qty'),
							cst_name: frm.doc.name,
							item_metadata: JSON.stringify({
								required_by: d2.get_value('required_by'),
							}),
						},
						callback(res) {
							const results = (res.message && res.message.results) || [];
							const ok = results.filter((x) => x.sent).length;
							frappe.show_alert({
								message: __('Sent rate request to {0} vendor(s)', [ok]),
								indicator: ok ? 'green' : 'orange',
							});
							d2.hide();
						},
					});
				},
			});
			d2.show();
		},
	});
}
