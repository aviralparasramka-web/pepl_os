# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors

import json

import frappe
from frappe import _
from frappe.utils import add_months, date_diff, flt, getdate, today


def _ensure_fallback_rm_group_for_bom_import():
    """Prefer Miscellaneous / Unclassified / Others; else create Miscellaneous."""
    for gn in ("Miscellaneous", "Unclassified", "Others"):
        if frappe.db.exists("PEPL RM Group", gn):
            return gn

    doc = frappe.get_doc(
        {
            "doctype": "PEPL RM Group",
            "group_name": "Miscellaneous",
            "material_base": "Other",
            "auto_sync_to_item_group": 0,
            "notes": (
                "<p>Auto-assigned for unclassified BOM components during CST "
                "Import from BOM. Map Item Groups to PEPL RM Groups for precise "
                "classification.</p>"
            ),
        }
    )
    doc.flags.ignore_permissions = True
    try:
        doc.insert()
        return doc.name
    except Exception:
        if frappe.db.exists("PEPL RM Group", "Miscellaneous"):
            return "Miscellaneous"
        raise


@frappe.whitelist()
def import_components_from_bom(cst_name):
    """Resolve CST → linked_item → default ERPNext BOM; return normalized per-unit components."""
    if not cst_name:
        return {
            "error": _("CST name required"),
            "components": [],
            "total_imported": 0,
            "unmapped_count": 0,
            "unmapped_items": [],
        }

    empty = {"components": [], "total_imported": 0, "unmapped_count": 0, "unmapped_items": []}

    cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)
    if not cst.linked_item:
        return {
            "error": _("CST has no linked item. Set Linked Product first."),
            **empty,
        }

    bom_name = frappe.db.get_value(
        "BOM",
        {
            "item": cst.linked_item,
            "is_default": 1,
            "is_active": 1,
            "docstatus": 1,
        },
        "name",
    )
    if not bom_name:
        return {
            "error": _("No active default submitted BOM for linked item."),
            **empty,
        }

    bom = frappe.get_doc("BOM", bom_name)
    bom_qty = flt(bom.quantity) or 1
    fallback_rm = _ensure_fallback_rm_group_for_bom_import()

    out = []
    unmapped_items = []

    for row in bom.items or []:
        ic = row.item_code
        if not ic:
            continue
        is_stock = frappe.db.get_value("Item", ic, "is_stock_item") or 0
        if not is_stock:
            continue

        is_product = frappe.db.get_value("Item", ic, "is_product") or 0
        mo = "Manufactured" if is_product else "Bought Out"
        qpa = flt(row.qty) / bom_qty

        drawing_no = frappe.db.get_value("Item", ic, "drawing_no") or ""

        item_group = frappe.db.get_value("Item", ic, "item_group") or ""
        rm_group = frappe.db.get_value(
            "PEPL RM Group", {"linked_item_group": item_group}, "name"
        )
        item_name = frappe.db.get_value("Item", ic, "item_name") or ic

        if not rm_group:
            rm_group = fallback_rm
            unmapped_items.append({"component_item": ic, "item_name": item_name})

        out.append(
            {
                "component_item": ic,
                "item_name": item_name,
                "quantity_per_assembly": round(qpa, 9),
                "uom": row.uom or frappe.db.get_value("Item", ic, "stock_uom") or "Nos",
                "rm_group": rm_group,
                "manufactured_or_bought_out": mo,
                "component_drawing_no": drawing_no,
            }
        )

    return {
        "error": None,
        "bom_name": bom_name,
        "components": out,
        "total_imported": len(out),
        "unmapped_count": len(unmapped_items),
        "unmapped_items": unmapped_items,
    }


@frappe.whitelist()
def get_rate_references(item_code):
    """Four rate sources for CST component costing."""
    if not item_code:
        frappe.throw(_("Item code required"))

    refs = []

    po_row = frappe.db.sql(
        """
        SELECT poi.rate AS rate, po.transaction_date AS pdate, po.name AS poname,
               po.supplier AS supplier
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.item_code = %s
          AND po.docstatus = 1
          AND IFNULL(po.status, '') NOT IN ('Closed', 'Cancelled', 'Completed')
        ORDER BY po.transaction_date DESC, po.modified DESC
        LIMIT 1
        """,
        (item_code,),
        as_dict=True,
    )
    if po_row:
        pr = po_row[0]
        pdate = getdate(pr.pdate) if pr.pdate else getdate(today())
        refs.append(
            {
                "rank": 1,
                "source": "Last Purchase Order",
                "rate": flt(pr.rate),
                "date": str(pr.pdate) if pr.pdate else None,
                "age_days": date_diff(getdate(today()), pdate),
                "reference_doc": pr.poname,
                "vendor": pr.supplier,
                "available": True,
            }
        )
    else:
        refs.append(
            {
                "rank": 1,
                "source": "Last Purchase Order",
                "rate": None,
                "date": None,
                "age_days": None,
                "reference_doc": None,
                "vendor": None,
                "available": False,
            }
        )

    sq_row = frappe.db.sql(
        """
        SELECT sqi.rate AS rate, sq.transaction_date AS tdate, sq.name AS sqname,
               sq.supplier AS supplier, sq.valid_till AS valid_till
        FROM `tabSupplier Quotation Item` sqi
        INNER JOIN `tabSupplier Quotation` sq ON sq.name = sqi.parent
        WHERE sqi.item_code = %s
          AND sq.docstatus = 1
          AND (
              sq.valid_till IS NULL OR sq.valid_till = ''
              OR sq.valid_till >= %s
          )
        ORDER BY sq.transaction_date DESC, sq.modified DESC
        LIMIT 1
        """,
        (item_code, getdate(today())),
        as_dict=True,
    )
    if sq_row:
        sr = sq_row[0]
        tdate = getdate(sr.tdate) if sr.tdate else getdate(today())
        refs.append(
            {
                "rank": 2,
                "source": "Last Supplier Quotation",
                "rate": flt(sr.rate),
                "date": str(sr.tdate) if sr.tdate else None,
                "age_days": date_diff(getdate(today()), tdate),
                "reference_doc": sr.sqname,
                "vendor": sr.supplier,
                "available": True,
            }
        )
    else:
        refs.append(
            {
                "rank": 2,
                "source": "Last Supplier Quotation",
                "rate": None,
                "date": None,
                "age_days": None,
                "reference_doc": None,
                "vendor": None,
                "available": False,
            }
        )

    lpr = frappe.db.get_value("Item", item_code, "last_purchase_rate")
    refs.append(
        {
            "rank": 3,
            "source": "Item.last_purchase_rate",
            "rate": flt(lpr) if lpr is not None else None,
            "date": None,
            "age_days": None,
            "reference_doc": None,
            "vendor": None,
            "available": lpr is not None and flt(lpr) > 0,
        }
    )

    vr = frappe.db.get_value("Item", item_code, "valuation_rate")
    refs.append(
        {
            "rank": 4,
            "source": "Item.valuation_rate",
            "rate": flt(vr) if vr is not None else None,
            "date": None,
            "age_days": None,
            "reference_doc": None,
            "vendor": None,
            "available": vr is not None and flt(vr) > 0,
        }
    )

    return {"references": refs}


def _item_spec_text(linked_item_code, linked_product):
    spec_parts = []
    if linked_product:
        pm = frappe.get_doc("PEPL Product Master", linked_product)
        for row in pm.specifications or []:
            if getattr(row, "spec_title", None):
                spec_parts.append(row.spec_title)
    item_desc = frappe.db.get_value("Item", linked_item_code, "description") if linked_item_code else None
    if item_desc and item_desc.strip():
        spec_parts.insert(0, item_desc.strip())
    return " | ".join(spec_parts) if spec_parts else ""


@frappe.whitelist()
def get_past_suppliers_for_item(item_code, lookback_months=18):
    """Distinct suppliers from submitted POs within lookback window."""
    if not item_code:
        frappe.throw(_("Item code required"))

    months = int(lookback_months) or 18
    cutoff = add_months(getdate(today()), -months)

    rows = frappe.db.sql(
        """
        SELECT po.supplier AS supplier,
               MAX(po.transaction_date) AS last_po_date,
               (SELECT poi.rate
                FROM `tabPurchase Order Item` poi
                INNER JOIN `tabPurchase Order` p2 ON p2.name = poi.parent
                WHERE poi.item_code = %s AND p2.supplier = po.supplier
                  AND p2.docstatus = 1
                ORDER BY p2.transaction_date DESC, poi.modified DESC
                LIMIT 1
               ) AS last_rate
        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
        WHERE poi.item_code = %s
          AND po.docstatus = 1
          AND po.transaction_date >= %s
        GROUP BY po.supplier
        ORDER BY last_po_date DESC
        """,
        (item_code, item_code, cutoff),
        as_dict=True,
    )

    out = []
    for r in rows:
        sup = r.supplier
        if not sup:
            continue
        out.append(
            {
                "supplier": sup,
                "supplier_name": frappe.db.get_value("Supplier", sup, "supplier_name") or sup,
                "last_po_date": str(r.last_po_date) if r.last_po_date else None,
                "last_rate": flt(r.last_rate) if r.last_rate is not None else None,
            }
        )
    return {"suppliers": out}


@frappe.whitelist()
def send_rfq_email_to_suppliers(
    item_code,
    supplier_list,
    qty,
    cst_name,
    item_metadata=None,
):
    """Compose and send RFQ emails; log Communication on CST."""
    if isinstance(supplier_list, str):
        supplier_list = json.loads(supplier_list)
    if isinstance(item_metadata, str):
        item_metadata = json.loads(item_metadata or "{}")
    item_metadata = item_metadata or {}

    if not item_code or not supplier_list:
        frappe.throw(_("Item and at least one supplier required"))

    item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
    drawing_no = item_metadata.get("drawing_no") or frappe.db.get_value("Item", item_code, "drawing_no") or ""
    drawing_rev = item_metadata.get("drawing_rev") or frappe.db.get_value("Item", item_code, "drawing_rev") or ""
    spec = item_metadata.get("specification") or ""

    qty_str = str(flt(qty) if qty else 1)
    req_by = item_metadata.get("required_by") or ""

    if not spec and cst_name:
        lp = frappe.db.get_value("PEPL CST Cost Sheet", cst_name, "linked_product")
        spec = _item_spec_text(item_code, lp)

    results = []
    for supplier in supplier_list:
        row = {"supplier": supplier, "sent": False, "error": None}
        try:
            email_id = frappe.db.get_value("Supplier", supplier, "email_id")
            if not email_id:
                row["error"] = _("No email on supplier record")
                results.append(row)
                continue

            body_lines = [
                f"Dear {frappe.db.get_value('Supplier', supplier, 'supplier_name') or supplier},",
                "",
                "Please share your current rate for the following:",
                "",
                f"Item: {item_name}",
                f"Drawing: {drawing_no} Rev {drawing_rev}",
                f"Specification: {spec or '—'}",
                f"Quantity: {qty_str}",
            ]
            if req_by:
                body_lines.append(f"Required by: {req_by}")
            body_lines.extend(
                [
                    f"Reference: PEPL CST {cst_name or '—'}",
                    "",
                    "Looking forward to your quotation.",
                    "",
                    "Regards,",
                    "Parasramka Engineering Pvt. Ltd.",
                ]
            )
            message = "\n".join(body_lines)

            frappe.sendmail(
                recipients=[email_id],
                subject=_("Rate request — {0}").format(item_code),
                message=message,
                reference_doctype="PEPL CST Cost Sheet" if cst_name else None,
                reference_name=cst_name or None,
                delayed=False,
            )

            try:
                comm = frappe.get_doc(
                    {
                        "doctype": "Communication",
                        "communication_type": "Communication",
                        "communication_medium": "Email",
                        "sent_or_received": "Sent",
                        "reference_doctype": "PEPL CST Cost Sheet" if cst_name else None,
                        "reference_name": cst_name or None,
                        "subject": _("Rate request — {0}").format(item_code),
                        "content": message,
                        "recipients": email_id,
                    }
                )
                comm.insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "CST RFQ Communication log")

            row["sent"] = True
        except Exception as e:
            row["error"] = str(e)
        results.append(row)

    return {"results": results}


def _cst_has_priced_component_lines(cst):
    """True if at least one component row has any costing amount."""
    for row in cst.components or []:
        if flt(row.component_subtotal) > 0:
            return True
        chunk = (
            flt(row.raw_material_cost)
            + flt(row.machining_cost)
            + flt(row.surface_treatment_cost)
            + flt(row.bought_out_cost)
            + flt(row.component_other_charges)
        )
        if chunk > 0:
            return True
    return False


@frappe.whitelist()
def create_quotation_from_cst(cst_name):
    """Draft Quotation from CST linked customer and item."""
    if not cst_name:
        frappe.throw(_("CST name required"))

    cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)

    if not cst.linked_product:
        frappe.throw(_("Set Linked Product on the CST first"))
    if not cst.linked_item:
        frappe.throw(_("CST has no linked item"))

    customer = cst.get("customer") or frappe.db.get_value(
        "PEPL Product Master", cst.linked_product, "primary_customer"
    )
    if not customer:
        frappe.throw(
            _("No customer on this Cost Sheet or its Linked Product (Primary Customer).")
        )

    if not _cst_has_priced_component_lines(cst):
        frappe.throw(
            _("Add at least one component line with cost before creating a quotation.")
        )

    rate = flt(cst.final_bid_price) or flt(cst.suggested_unit_price)
    if not rate:
        frappe.throw(_("Set Final Bid Price or ensure Suggested Unit Price is calculated"))

    company = frappe.defaults.get_user_default("company") or frappe.db.get_single_value(
        "Global Defaults", "default_company"
    )

    qtn = frappe.new_doc("Quotation")
    qtn.quotation_to = "Customer"
    qtn.party_name = customer
    qtn.company = company
    qtn.transaction_date = today()
    qtn.valid_till = add_months(getdate(today()), 1)

    if company:
        qtn.currency = frappe.db.get_value("Company", company, "default_currency") or "INR"

    qtn.append(
        "items",
        {
            "item_code": cst.linked_item,
            "qty": 1,
            "rate": rate,
        },
    )

    qtn.flags.ignore_permissions = True
    qtn.insert()
    return {"name": qtn.name}


@frappe.whitelist()
def get_quotation_email_context(quotation_name):
    """Subject, recipients, HTML body for customer quotation email."""
    if not quotation_name:
        frappe.throw(_("Quotation name required"))

    q = frappe.get_doc("Quotation", quotation_name)
    cust = q.party_name if q.quotation_to == "Customer" else None
    if not cust:
        frappe.throw(_("Quotation must be for a Customer"))

    recipients = q.contact_email or frappe.db.get_value("Customer", cust, "email_id")
    subject = _("Quotation {0} from Parasramka Engineering").format(q.name)

    body = f"""<p>Dear Customer,</p>
<p>Please find our quotation <strong>{frappe.utils.escape_html(q.name)}</strong> for your consideration.</p>
<p>We remain at your disposal for any clarifications.</p>
<p>Best regards,<br/>
Parasramka Engineering Pvt. Ltd.</p>
"""

    return {
        "recipients": recipients or "",
        "subject": subject,
        "message": body,
    }


