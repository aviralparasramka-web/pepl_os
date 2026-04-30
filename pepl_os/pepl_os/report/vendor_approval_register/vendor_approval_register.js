frappe.query_reports["Vendor Approval Register"] = {
	filters: [
		{
			fieldname: "status",
			label: __("Approval Status"),
			fieldtype: "Select",
			options: "All\nApproved\nIn Progress\nUnapproved",
			default: "All"
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
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "approval_status" && data) {
			if (data.approval_status === "Approved") {
				value = `<span style="color: green; font-weight: bold;">${data.approval_status}</span>`;
			} else if (data.approval_status === "In Progress") {
				value = `<span style="color: orange; font-weight: bold;">${data.approval_status}</span>`;
			} else if (data.approval_status === "Unapproved") {
				value = `<span style="color: red; font-weight: bold;">${data.approval_status}</span>`;
			}
		}

		return value;
	}
};
