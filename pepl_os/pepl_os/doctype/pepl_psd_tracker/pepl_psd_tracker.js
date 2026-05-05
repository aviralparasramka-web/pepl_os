frappe.ui.form.on("PEPL PSD Tracker", {
	refresh(frm) {
		if (frm.doc.psd_status) {
			const colours = {
				"Pending": "orange",
				"Requested to Bank": "blue",
				"Received from Bank / Dispatched to Customer": "blue",
				"Active": "green",
				"NDC Submission": "yellow",
				"PSD Refunded": "green",
				"Letter to Bank for Closure": "yellow",
				"Closed": "darkgrey",
				"PSD Not Required": "grey"
			};
			frm.page.set_indicator(
				frm.doc.psd_status,
				colours[frm.doc.psd_status] || "grey"
			);
		}
	},

	order_value(frm) {
		_calc_psd_amount(frm);
	},

	psd_percentage(frm) {
		_calc_psd_amount(frm);
	},

	last_supply_date(frm) {
		if (frm.doc.last_supply_date) {
			const d = frappe.datetime.add_months(frm.doc.last_supply_date, 14);
			frm.set_value("expected_refund_date", d);
		}
	}
});

function _calc_psd_amount(frm) {
	const val = flt(frm.doc.order_value) * flt(frm.doc.psd_percentage) / 100;
	frm.set_value("psd_amount", val);
}
