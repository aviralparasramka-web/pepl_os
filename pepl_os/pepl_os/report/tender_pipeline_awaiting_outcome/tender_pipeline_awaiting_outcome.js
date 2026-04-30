frappe.query_reports["Tender Pipeline Awaiting Outcome"] = {
	filters: [
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "days_pending" && data && data.days_pending !== null) {
			const days = data.days_pending;
			if (days > 60) {
				value = `<span style="color: red; font-weight: bold;">${days} days \u26a0</span>`;
			} else if (days > 30) {
				value = `<span style="color: orange; font-weight: bold;">${days} days</span>`;
			}
		}

		return value;
	}
};
