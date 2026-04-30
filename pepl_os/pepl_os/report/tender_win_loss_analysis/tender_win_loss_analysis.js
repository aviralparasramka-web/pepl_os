frappe.query_reports["Tender Win/Loss Analysis"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -6)
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
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "status",
			label: __("Outcome"),
			fieldtype: "Select",
			options: "\nWon\nLost\nPartially Won"
		},
		{
			fieldname: "loss_reason",
			label: __("Loss Reason"),
			fieldtype: "Select",
			options: "\nPrice\nTechnical\nDelivery\nRelationship\nVendor Status\nOther"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "status" && data) {
			if (data.status === "Won") {
				value = `<span style="color: green; font-weight: bold;">${data.status}</span>`;
			} else if (data.status === "Lost") {
				value = `<span style="color: red; font-weight: bold;">${data.status}</span>`;
			} else if (data.status === "Partially Won") {
				value = `<span style="color: #ffc107; font-weight: bold;">${data.status}</span>`;
			}
		}

		return value;
	}
};
