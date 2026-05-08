"""Ensure PEPL CST Component cost columns stay editable and visible in the grid."""

import frappe


def execute():
    for fn in (
        "raw_material_cost",
        "machining_cost",
        "surface_treatment_cost",
        "bought_out_cost",
        "component_other_charges",
    ):
        frappe.make_property_setter(
            {
                "doctype": "PEPL CST Component",
                "doctype_or_field": "DocField",
                "fieldname": fn,
                "property": "read_only",
                "value": "0",
                "property_type": "Check",
            },
            validate_fields_for_doctype=False,
        )
        frappe.make_property_setter(
            {
                "doctype": "PEPL CST Component",
                "doctype_or_field": "DocField",
                "fieldname": fn,
                "property": "in_list_view",
                "value": "1",
                "property_type": "Check",
            },
            validate_fields_for_doctype=False,
        )
    frappe.db.commit()
