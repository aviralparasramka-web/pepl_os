frappe.query_reports["Competitor Analysis"] = {
	filters: [
		{
			fieldname: "competitor_name",
			label: __("Competitor Name (Search)"),
			fieldtype: "Data",
			description: "Type any part of competitor name to filter"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers"
		},
		{
			fieldname: "outcome",
			label: __("Outcome"),
			fieldtype: "Select",
			options: "\nWon\nLost"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "outcome" && data) {
			if (data.outcome === "Won") {
				value = `<span style="color: green; font-weight: bold;">${data.outcome}</span>`;
			} else if (data.outcome === "Lost") {
				value = `<span style="color: red; font-weight: bold;">${data.outcome}</span>`;
			}
		}

		return value;
	}
};
