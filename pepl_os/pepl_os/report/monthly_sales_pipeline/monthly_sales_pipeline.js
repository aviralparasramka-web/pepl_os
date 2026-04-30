frappe.query_reports["Monthly Sales Pipeline"] = {
	filters: [
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			options: "2024\n2025\n2026\n2027",
			default: "2026"
		},
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers"
		}
	]
};
