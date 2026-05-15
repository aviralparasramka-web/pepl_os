// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
// PEPL Quotation Comparison — form script
//
// Renders the rich side-by-side comparison grid into the
// comparison_grid HTML field. Wires up live total computation
// and provides Refresh Quotes + Approve buttons.

frappe.ui.form.on("PEPL Quotation Comparison", {
    refresh: function(frm) {
        // Buttons
        if (frm.doc.status === "Draft" || frm.doc.status === "Pending Approval") {
            frm.add_custom_button(__("Refresh Quotes"), () => pepl_refresh_quotes(frm));

            if (frappe.user.has_role("Purchase Manager") || frappe.user.has_role("System Manager")) {
                frm.add_custom_button(__("Approve & Create POs"), () => pepl_approve(frm))
                    .addClass("btn-primary");
            }
        }

        if (frm.doc.status === "Approved" && frm.doc.generated_pos) {
            frm.add_custom_button(__("View Generated POs"), () => pepl_view_pos(frm));
        }

        // Render grid
        if (frm.doc.name && !frm.is_new()) {
            pepl_render_grid(frm);
        }
    },

    after_save: function(frm) {
        if (frm.doc.name && !frm.is_new()) {
            pepl_render_grid(frm);
        }
    }
});


// Module-level cache: comparison_name -> grid data
const PEPL_GRID_DATA = {};


function pepl_render_grid(frm) {
    if (!frm.fields_dict.comparison_grid) {
        console.warn("PEPL: comparison_grid HTML field missing on form");
        return;
    }

    const $wrapper = $(frm.fields_dict.comparison_grid.wrapper);
    $wrapper.html('<div class="text-muted" style="padding:12px;">Loading comparison data\u2026</div>');

    frappe.call({
        method: "pepl_os.pepl_os.api.quotation_comparison.get_comparison_data",
        args: { comparison_name: frm.doc.name, months: 24 },
        callback: function(r) {
            if (!r.message || Object.keys(r.message).length === 0) {
                $wrapper.html('<div class="text-muted" style="padding:12px;">No items yet. The linked RFQ may not be submitted.</div>');
                return;
            }

            PEPL_GRID_DATA[frm.doc.name] = r.message;

            const html = pepl_build_grid_html(r.message, frm.doc.comparison_items || [], frm.doc.status);
            $wrapper.html(html);

            pepl_attach_handlers($wrapper, frm);
            pepl_update_all_totals($wrapper, frm);
        }
    });
}


function pepl_build_grid_html(data, comparison_items, status) {
    const is_readonly = (status === "Approved" || status === "Cancelled");

    let html = "<style>" + pepl_grid_css() + "</style>";
    html += '<div class="pepl-comparison-grid">';

    for (const [item_code, item_data] of Object.entries(data)) {
        const vendors = item_data.vendors || {};
        const vendor_list = Object.keys(vendors).sort();

        html += `<div class="pepl-item-block" data-item="${pepl_esc(item_code)}">`;

        // Item header
        html += `<div class="pepl-item-header">`;
        html += `<div class="pepl-item-name">${pepl_esc(item_data.item_name || item_code)}</div>`;
        html += `<div class="pepl-item-code">${pepl_esc(item_code)}</div>`;
        html += `<div class="pepl-meta">Required: <strong>${item_data.required_qty} ${pepl_esc(item_data.uom || "")}</strong> &nbsp;|&nbsp; Required by: ${item_data.required_by || "\u2014"}</div>`;
        html += `</div>`;

        if (vendor_list.length === 0) {
            html += '<div class="pepl-no-vendors">No quotes received and no historical rates for this item.</div></div>';
            continue;
        }

        // Vendor columns
        html += `<div class="pepl-vendor-row">`;
        for (const vendor of vendor_list) {
            html += pepl_render_vendor_col(item_code, vendor, vendors[vendor], comparison_items, is_readonly);
        }
        html += `</div>`;

        // Allocation summary
        if (!is_readonly) {
            html += `<div class="pepl-allocation-summary" data-item="${pepl_esc(item_code)}">`;
            html += `<div class="pepl-totals-text">Allocated: <span class="pepl-totals-value">0</span> / <strong>${item_data.required_qty}</strong> ${pepl_esc(item_data.uom || "")}</div>`;
            html += `<input type="text" placeholder="If allocation \u2260 required: enter reason here" class="pepl-qty-reason form-control" data-item="${pepl_esc(item_code)}" />`;
            html += `</div>`;
        } else {
            const total = comparison_items.filter(r => r.item_code === item_code).reduce((s, r) => s + (parseFloat(r.qty) || 0), 0);
            html += `<div class="pepl-allocation-summary pepl-readonly"><div class="pepl-totals-text">Final allocation: <strong>${total}</strong> / ${item_data.required_qty}</div></div>`;
        }

        html += `</div>`;
    }

    html += "</div>";
    return html;
}


function pepl_render_vendor_col(item_code, vendor, v_data, comparison_items, is_readonly) {
    const cq = v_data.current_quote;
    const allocated = pepl_get_allocation(comparison_items, item_code, vendor);

    let html = `<div class="pepl-vendor-col" data-vendor="${pepl_esc(vendor)}">`;
    html += `<div class="pepl-vendor-name">${pepl_esc(vendor)}</div>`;

    // Current quote
    if (cq) {
        html += `<div class="pepl-current-quote">\u20b9${cq.rate.toFixed(2)}`;
        if (cq.ranking) html += ` <span class="pepl-rank">L${cq.ranking}</span>`;
        html += `</div>`;
        html += `<div class="pepl-lead-time">Lead: ${cq.lead_time_days} day(s)</div>`;
    } else {
        html += `<div class="pepl-current-quote pepl-na">\u2014 NA \u2014</div>`;
        html += `<div class="pepl-lead-time">Did not quote</div>`;
    }

    // History
    if (v_data.history && v_data.history.length > 0) {
        html += `<div class="pepl-history">`;
        html += `<div class="pepl-history-label">Last 24mo (${v_data.history.length} rec):</div>`;
        for (const h of v_data.history.slice(0, 4)) {
            const dt = h.date ? h.date.slice(0, 7) : "\u2014";
            html += `<div class="pepl-history-row"><span class="pepl-h-date">${dt}</span> <span class="pepl-h-src">${h.source}</span> <span class="pepl-h-rate">\u20b9${h.rate.toFixed(2)}</span></div>`;
        }
        if (v_data.history.length > 4) {
            html += `<div class="pepl-history-more">+${v_data.history.length - 4} more\u2026</div>`;
        }
        html += `</div>`;
    } else {
        html += `<div class="pepl-history pepl-no-history">No prior rates</div>`;
    }

    // Allocation inputs
    if (!is_readonly) {
        const default_rate = allocated.rate || (cq ? cq.rate : "");
        html += `<div class="pepl-allocation-inputs">`;
        html += `<label class="pepl-input-label">Allocate qty</label>`;
        html += `<input type="number" step="0.01" min="0" class="pepl-qty-input form-control" data-item="${pepl_esc(item_code)}" data-vendor="${pepl_esc(vendor)}" value="${allocated.qty || ""}" />`;
        html += `<label class="pepl-input-label">Rate to use</label>`;
        html += `<input type="number" step="0.01" min="0" class="pepl-rate-input form-control" data-item="${pepl_esc(item_code)}" data-vendor="${pepl_esc(vendor)}" value="${default_rate}" />`;
        html += `<label class="pepl-input-label pepl-reason-label" style="display:none;">Rate override reason</label>`;
        html += `<input type="text" class="pepl-reason-input form-control" data-item="${pepl_esc(item_code)}" data-vendor="${pepl_esc(vendor)}" value="${pepl_esc(allocated.reason || "")}" placeholder="Why?" style="display:none;" />`;
        html += `</div>`;
    } else if (allocated.qty > 0) {
        html += `<div class="pepl-final-alloc"><strong>Awarded</strong><br>${allocated.qty} @ \u20b9${allocated.rate.toFixed(2)}</div>`;
    }

    html += `</div>`;
    return html;
}


function pepl_get_allocation(comparison_items, item_code, vendor) {
    const row = (comparison_items || []).find(r => r.item_code === item_code && r.selected_vendor === vendor);
    if (!row) return { qty: 0, rate: 0, reason: "" };
    return { qty: row.qty || 0, rate: row.selected_rate || 0, reason: row.override_reason || "" };
}


function pepl_attach_handlers($wrapper, frm) {
    $wrapper.find(".pepl-qty-input, .pepl-rate-input").on("change input", function() {
        const item = $(this).data("item");
        const vendor = $(this).data("vendor");
        pepl_sync_allocation(frm, $wrapper, item, vendor);
        pepl_update_item_totals($wrapper, frm, item);
        frm.dirty();
    });

    $wrapper.find(".pepl-reason-input").on("change input", function() {
        const item = $(this).data("item");
        const vendor = $(this).data("vendor");
        pepl_sync_allocation(frm, $wrapper, item, vendor);
        frm.dirty();
    });
}


function pepl_sync_allocation(frm, $wrapper, item_code, vendor) {
    const data = PEPL_GRID_DATA[frm.doc.name] || {};
    const vendor_info = data?.[item_code]?.vendors?.[vendor];
    const original_rate = vendor_info?.current_quote?.rate || 0;

    const $col = $wrapper.find('.pepl-vendor-col').filter(function() {
        return $(this).data("vendor") === vendor &&
               $(this).closest(".pepl-item-block").data("item") === item_code;
    });

    const qty = parseFloat($col.find(".pepl-qty-input").val()) || 0;
    const rate = parseFloat($col.find(".pepl-rate-input").val()) || 0;
    const reason = $col.find(".pepl-reason-input").val() || "";

    const rate_differs = original_rate > 0 && Math.abs(rate - original_rate) > 0.01;
    $col.find(".pepl-reason-label, .pepl-reason-input").toggle(rate_differs && qty > 0);

    let row = (frm.doc.comparison_items || []).find(r => r.item_code === item_code && r.selected_vendor === vendor);

    if (qty > 0) {
        if (row) {
            row.qty = qty;
            row.selected_rate = rate;
            row.override_reason = rate_differs ? reason : "";
        } else {
            const required_qty = pepl_get_required_qty(frm, item_code);
            row = frm.add_child("comparison_items", {
                item_code: item_code,
                required_qty: required_qty,
                qty: qty,
                selected_vendor: vendor,
                selected_rate: rate,
                original_quoted_rate: original_rate,
                override_reason: rate_differs ? reason : ""
            });
        }
    } else if (row) {
        frm.doc.comparison_items = (frm.doc.comparison_items || []).filter(r => r !== row);
    }

    frm.refresh_field("comparison_items");
}


function pepl_get_required_qty(frm, item_code) {
    const data = PEPL_GRID_DATA[frm.doc.name] || {};
    return data?.[item_code]?.required_qty || 0;
}


function pepl_update_item_totals($wrapper, frm, item_code) {
    const total = (frm.doc.comparison_items || [])
        .filter(r => r.item_code === item_code)
        .reduce((s, r) => s + (parseFloat(r.qty) || 0), 0);

    const required = pepl_get_required_qty(frm, item_code);
    const $summary = $wrapper.find('.pepl-allocation-summary').filter(function() {
        return $(this).data("item") === item_code;
    });
    $summary.find(".pepl-totals-value").text(total.toFixed(2));

    const mismatch = Math.abs(total - required) > 0.01 && total > 0;
    $summary.toggleClass("pepl-mismatch", mismatch);
    $summary.toggleClass("pepl-matched", !mismatch && total > 0);
}


function pepl_update_all_totals($wrapper, frm) {
    $wrapper.find(".pepl-item-block").each(function() {
        const item_code = $(this).data("item");
        pepl_update_item_totals($wrapper, frm, item_code);
    });
}


function pepl_refresh_quotes(frm) {
    frappe.show_alert({ message: __("Refreshing vendor responses\u2026"), indicator: "blue" });
    frappe.call({
        method: "pepl_os.pepl_os.api.quotation_comparison.sync_responses",
        args: { comparison_name: frm.doc.name },
        callback: function(r) {
            if (r.message && r.message.status === "refreshed") {
                frappe.show_alert({
                    message: __("Refreshed: ") + r.message.response_count + " " + __("response(s)"),
                    indicator: "green"
                });
                frm.reload_doc();
            } else if (r.message && r.message.status === "skipped") {
                frappe.msgprint(__("Skipped: ") + r.message.reason);
            }
        }
    });
}


function pepl_approve(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__("Save your changes before approving."));
        return;
    }

    pepl_save_qty_overrides(frm).then(() => {
        frappe.confirm(
            __("This will create draft Purchase Orders, one per winning vendor. Status moves to Approved. Proceed?"),
            function() {
                frappe.dom.freeze(__("Creating Purchase Orders\u2026"));
                frappe.call({
                    method: "pepl_os.pepl_os.api.quotation_comparison.approve_comparison",
                    args: { comparison_name: frm.doc.name },
                    callback: function(r) {
                        frappe.dom.unfreeze();
                        if (r.message && r.message.length > 0) {
                            const links = r.message.map(po => `<a href="/app/purchase-order/${po}">${po}</a>`).join(", ");
                            frappe.msgprint({
                                title: __("Comparison Approved"),
                                message: __("Draft Purchase Orders created: ") + links,
                                indicator: "green"
                            });
                            frm.reload_doc();
                        }
                    },
                    error: function() {
                        frappe.dom.unfreeze();
                    }
                });
            }
        );
    });
}


function pepl_save_qty_overrides(frm) {
    const $wrapper = $(frm.fields_dict.comparison_grid.wrapper);
    const promises = [];

    $wrapper.find(".pepl-allocation-summary.pepl-mismatch").each(function() {
        const item = $(this).data("item");
        const reason = $(this).find(".pepl-qty-reason").val();
        if (reason && reason.trim()) {
            promises.push(frappe.call({
                method: "pepl_os.pepl_os.api.quotation_comparison.record_qty_override",
                args: { comparison_name: frm.doc.name, item_code: item, reason: reason.trim() }
            }));
        }
    });

    return promises.length > 0 ? Promise.all(promises) : Promise.resolve();
}


function pepl_view_pos(frm) {
    if (!frm.doc.generated_pos) return;
    const po_names = frm.doc.generated_pos.split(",").map(s => s.trim()).filter(Boolean);
    frappe.set_route("List", "Purchase Order", { name: ["in", po_names] });
}


// Helpers
function pepl_esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function(m) {
        return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[m];
    });
}


function pepl_grid_css() {
    return `
.pepl-comparison-grid { padding: 8px 0; font-size: 13px; }
.pepl-item-block { border: 1px solid #d4d3cd; border-radius: 8px; margin-bottom: 16px; padding: 12px; background: #fdfcf7; }
.pepl-item-header { padding-bottom: 8px; border-bottom: 1px solid #e8e7e0; margin-bottom: 10px; }
.pepl-item-name { font-weight: 600; color: #1a3a5c; font-size: 14px; }
.pepl-item-code { font-family: monospace; font-size: 11px; color: #73726c; }
.pepl-meta { font-size: 12px; color: #5f5e5a; margin-top: 4px; }
.pepl-vendor-row { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 6px; }
.pepl-vendor-col { flex: 0 0 200px; border: 1px solid #e8e7e0; border-radius: 6px; padding: 10px; background: white; }
.pepl-vendor-name { font-weight: 600; color: #1a3a5c; font-size: 13px; }
.pepl-current-quote { font-size: 16px; margin-top: 6px; color: #0f6e56; font-weight: 600; }
.pepl-current-quote.pepl-na { color: #a32d2d; font-style: italic; font-weight: 400; }
.pepl-rank { font-size: 10px; color: #854f0b; background: #ffeed4; padding: 2px 5px; border-radius: 3px; font-weight: 600; }
.pepl-lead-time { font-size: 11px; color: #73726c; margin-top: 2px; }
.pepl-history { margin-top: 8px; padding-top: 6px; border-top: 1px dashed #e8e7e0; }
.pepl-history.pepl-no-history { color: #73726c; font-style: italic; font-size: 11px; }
.pepl-history-label { font-size: 10px; color: #73726c; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }
.pepl-history-row { font-size: 11px; color: #3d3d3a; display: flex; gap: 4px; }
.pepl-h-date { color: #73726c; min-width: 50px; }
.pepl-h-src { color: #854f0b; min-width: 18px; font-weight: 600; }
.pepl-h-rate { color: #1a3a5c; }
.pepl-history-more { font-size: 10px; color: #73726c; font-style: italic; margin-top: 2px; }
.pepl-allocation-inputs { margin-top: 10px; padding-top: 8px; border-top: 1px solid #e8e7e0; }
.pepl-input-label { display: block; font-size: 10px; color: #73726c; text-transform: uppercase; margin: 4px 0 2px; letter-spacing: 0.3px; }
.pepl-allocation-inputs .form-control { padding: 4px 6px; font-size: 12px; height: 26px; }
.pepl-final-alloc { margin-top: 10px; padding: 8px; background: #e6f4ea; border-radius: 4px; font-size: 12px; }
.pepl-allocation-summary { margin-top: 10px; padding: 8px 12px; background: #fafaf5; border-radius: 4px; border: 1px solid #e8e7e0; }
.pepl-allocation-summary.pepl-matched { background: #e6f4ea; border-color: #b3d9b8; }
.pepl-allocation-summary.pepl-mismatch { background: #fff4e0; border-color: #f0c987; }
.pepl-totals-text { font-size: 12px; color: #3d3d3a; }
.pepl-allocation-summary.pepl-mismatch .pepl-totals-value { color: #a32d2d; font-weight: 600; }
.pepl-allocation-summary.pepl-matched .pepl-totals-value { color: #0f6e56; font-weight: 600; }
.pepl-qty-reason { margin-top: 6px; font-size: 12px; height: 28px; display: none; }
.pepl-allocation-summary.pepl-mismatch .pepl-qty-reason { display: block; }
.pepl-no-vendors { padding: 12px; color: #73726c; font-style: italic; text-align: center; }
.pepl-readonly { background: #fafaf5; }
    `;
}
