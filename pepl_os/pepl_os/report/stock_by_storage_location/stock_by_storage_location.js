// Copyright (c) 2026, Parasramka Engineering Pvt. Ltd.
frappe.query_reports["Stock by Storage Location"] = {
    filters: [
        {fieldname: "warehouse", label: "Warehouse", fieldtype: "Link",
         options: "Warehouse"},
        {fieldname: "rack_number", label: "Rack Number", fieldtype: "Data"},
        {fieldname: "bin_number", label: "Bin Number", fieldtype: "Data"},
        {fieldname: "item_code", label: "Item", fieldtype: "Link",
         options: "Item"},
        {fieldname: "qc_status", label: "QC Status", fieldtype: "Select",
         options: "\nNot Required\nPending\nPassed\nFailed"}
    ]
};
