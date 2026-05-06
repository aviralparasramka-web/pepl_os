// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
// Stock & Pipeline dashboard panel for Material Request

frappe.ui.form.on('Material Request', {
    refresh(frm) {
        render_supply_dashboard(frm);
    },
    items_remove(frm) {
        render_supply_dashboard(frm);
    },
});

frappe.ui.form.on('Material Request Item', {
    item_code(frm, cdt, cdn) {
        // Slight delay so item fetch completes
        setTimeout(() => render_supply_dashboard(frm), 300);
    },
    qty(frm, cdt, cdn) {
        render_supply_dashboard(frm);
    },
});

function render_supply_dashboard(frm) {
    const target_field = frm.fields_dict.pepl_supply_dashboard_html;
    if (!target_field) return;  // Custom field not yet deployed

    const items = (frm.doc.items || []).filter(r => r.item_code);
    if (!items.length) {
        target_field.$wrapper.html(
            '<div style="padding:8px 0;color:#888;font-style:italic;">' +
            'Add items to the table below to see Stock & Pipeline position.</div>'
        );
        return;
    }

    const item_codes = [...new Set(items.map(r => r.item_code))];

    frappe.call({
        method: 'pepl_os.pepl_os.api.inventory_intelligence.get_items_supply_position',
        args: { item_codes: JSON.stringify(item_codes) },
        freeze: false,
        callback(r) {
            if (!r.message) return;
            const html = build_dashboard_html(items, r.message);
            target_field.$wrapper.html(html);
        }
    });
}

function build_dashboard_html(items, positions) {
    // Aggregate qty per item_code (in case same item appears multiple times)
    const agg = {};
    for (const it of items) {
        const code = it.item_code;
        if (!agg[code]) {
            agg[code] = { qty: 0, pos: positions[code] || {in_stock:0, on_order:0, open_mr:0} };
        }
        agg[code].qty += parseFloat(it.qty) || 0;
    }

    let html = '<div style="margin:8px 0 4px 0;font-weight:600;color:#1F4E79;">' +
               '📊 Stock &amp; Pipeline Position</div>';
    html += '<table class="table table-bordered" style="font-size:12px;margin-bottom:0;">';
    html += '<thead><tr style="background:#1F4E79;color:#fff;">' +
            '<th>Item</th>' +
            '<th style="text-align:right;">In Stock</th>' +
            '<th style="text-align:right;">On Order</th>' +
            '<th style="text-align:right;">Open MRs</th>' +
            '<th style="text-align:right;">This MR</th>' +
            '<th style="text-align:right;">Total Supply After</th>' +
            '</tr></thead><tbody>';

    for (const [code, data] of Object.entries(agg)) {
        const total = data.pos.in_stock + data.pos.on_order + data.pos.open_mr + data.qty;
        const fmt = (n) => (Math.round(n * 100) / 100).toLocaleString('en-IN');
        const stock_color = data.pos.in_stock > 0 ? '#2E7D32' : '#888';
        html += `<tr>
            <td><b>${frappe.utils.escape_html(code)}</b></td>
            <td style="text-align:right;color:${stock_color};">${fmt(data.pos.in_stock)}</td>
            <td style="text-align:right;">${fmt(data.pos.on_order)}</td>
            <td style="text-align:right;">${fmt(data.pos.open_mr)}</td>
            <td style="text-align:right;background:#FFF3CD;"><b>${fmt(data.qty)}</b></td>
            <td style="text-align:right;font-weight:600;background:#E8F5E9;">${fmt(total)}</td>
        </tr>`;
    }

    html += '</tbody></table>';
    html += '<div style="margin-top:6px;color:#666;font-size:11px;font-style:italic;">' +
            'Yellow = quantity from this MR &nbsp;·&nbsp; Green = total supply after this MR is fulfilled' +
            '</div>';
    return html;
}
