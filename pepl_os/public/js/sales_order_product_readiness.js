// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

frappe.ui.form.on('Sales Order', {
    refresh(frm) {
        render_product_readiness(frm);
    },
    items_on_form_rendered(frm) {
        render_product_readiness(frm);
    },
    items_add(frm) {
        render_product_readiness(frm);
    },
    items_remove(frm) {
        render_product_readiness(frm);
    },
});

frappe.ui.form.on('Sales Order Item', {
    item_code(frm) {
        render_product_readiness(frm);
    },
    qty(frm) {
        render_product_readiness(frm);
    },
});

function render_product_readiness(frm) {
    const target = frm.fields_dict.product_readiness_html;
    if (!target) return;

    if (frm.is_new()) {
        target.$wrapper.html(
            '<div class="alert alert-info" style="margin-bottom:0;">Save the record first to load Product Readiness.</div>'
        );
        return;
    }

    frappe.call({
        method: 'pepl_os.pepl_os.api.readiness_intelligence.get_so_product_readiness',
        args: { sales_order_name: frm.doc.name },
        freeze: false,
        callback(r) {
            if (!r.message) return;
            target.$wrapper.html(build_so_html(r.message));
            target.$wrapper
                .off('click.pepl_pr')
                .on('click.pepl_pr', '.pepl-product-readiness-refresh', () =>
                    render_product_readiness(frm)
                );
        },
    });
}

function icon_product(st) {
    if (st === 'green') return '🟢';
    if (st === 'yellow') return '🟡';
    if (st === 'red') return '🔴';
    if (st === 'no_bom') return '<span title="No BOM">⚪ No BOM</span>';
    return '⚪';
}

function icon_component(st) {
    return icon_product(st === 'no_bom' ? 'green' : st);
}

function esc(s) {
    return frappe.utils.escape_html(String(s == null ? '' : s));
}

function fmt(n) {
    const x = parseFloat(n);
    if (Number.isNaN(x)) return '0';
    return (Math.round(x * 1000000) / 1000000).toLocaleString('en-IN');
}

function build_so_html(data) {
    const lines = data.line_items || [];

    let html = '<div style="padding:4px 0 8px;">';
    html +=
        '<button type="button" class="btn btn-xs btn-default pepl-product-readiness-refresh">' +
        'Refresh readiness</button>';

    html += '<div style="margin:12px 0 6px;font-weight:600;color:#1F4E79;">Product lines</div>';
    html += '<div class="table-responsive">';
    html += '<table class="table table-bordered table-condensed" style="font-size:12px;margin-bottom:12px;">';
    html +=
        '<thead><tr style="background:#1F4E79;color:#fff;">' +
        '<th></th><th>Product</th><th style="text-align:right;">Line qty</th>' +
        '<th>BOM</th></tr></thead><tbody>';

    for (const row of lines) {
        const pst = row.product_status || '';
        const pi = icon_product(pst);
        const bomlbl = esc(row.bom_source || '—') + (row.bom_name ? ' · ' + esc(row.bom_name) : '');
        html += '<tr>';
        html += '<td style="font-size:16px;">' + pi + '</td>';
        html +=
            '<td><strong>' +
            esc(row.item_code) +
            '</strong><br><small>' +
            esc(row.item_name) +
            '</small></td>';
        html += '<td style="text-align:right;">' + fmt(row.line_qty) + '</td>';
        html += '<td>' + bomlbl + '</td>';
        html += '</tr>';
    }

    if (!lines.length) {
        html +=
            '<tr><td colspan="4" style="color:#888;font-style:italic;">No product lines (enable <code>is_product</code> on Item).</td></tr>';
    }

    html += '</tbody></table></div>';

    for (const row of lines) {
        const comps = row.components || [];
        if (!comps.length) continue;
        html +=
            '<div style="margin:8px 0 4px;font-weight:600;font-size:12px;">Components — ' +
            esc(row.item_code) +
            '</div>';
        html += '<div class="table-responsive">';
        html +=
            '<table class="table table-bordered table-condensed" style="font-size:11px;margin-bottom:14px;">';
        html +=
            '<thead><tr style="background:#eee;">' +
            '<th></th><th>Component</th><th style="text-align:right;">Req</th>' +
            '<th style="text-align:right;">Stock</th><th style="text-align:right;">PO</th>' +
            '<th style="text-align:right;">MR</th><th style="text-align:right;">Short</th>' +
            '<th>LT</th></tr></thead><tbody>';
        for (const c of comps) {
            const sub = c.sub_assembly ? '📦 ' : '';
            html += '<tr>';
            html += '<td>' + icon_component(c.status) + '</td>';
            html +=
                '<td>' +
                sub +
                '<strong>' +
                esc(c.item_code) +
                '</strong><br><small>' +
                esc(c.item_name) +
                '</small></td>';
            html += '<td style="text-align:right;">' + fmt(c.required_qty) + '</td>';
            html += '<td style="text-align:right;">' + fmt(c.in_stock) + '</td>';
            html += '<td style="text-align:right;">' + fmt(c.on_order) + '</td>';
            html += '<td style="text-align:right;">' + fmt(c.open_mr) + '</td>';
            html += '<td style="text-align:right;">' + fmt(c.shortfall) + '</td>';
            html += '<td>' + esc(c.lead_time_days) + ' d</td>';
            html += '</tr>';
        }
        html += '</tbody></table></div>';
    }

    html += '</div>';
    return html;
}
