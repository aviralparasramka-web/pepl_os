frappe.query_reports["CST History (Per Item)"] = {
	filters: [
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item",
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers"
		}
	]
};
