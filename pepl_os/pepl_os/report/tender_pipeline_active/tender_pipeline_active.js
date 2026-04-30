frappe.query_reports["Tender Pipeline (Active)"] = {
	filters: [
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers",
			default: ""
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "from_date",
			label: __("Deadline From"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("Deadline To"),
			fieldtype: "Date"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "days_remaining" && data) {
			const days = data.days_remaining;
			if (days !== null && days !== undefined) {
				if (days < 0) {
					value = `<span style="color: red; font-weight: bold;">EXPIRED (${Math.abs(days)}d ago)</span>`;
				} else if (days <= 1) {
					value = `<span style="color: red; font-weight: bold;">${days} day(s) \u26a0</span>`;
				} else if (days <= 3) {
					value = `<span style="color: orange; font-weight: bold;">${days} days</span>`;
				} else if (days <= 7) {
					value = `<span style="color: #f39c12;">${days} days</span>`;
				}
			}
		}

		return value;
	}
};
