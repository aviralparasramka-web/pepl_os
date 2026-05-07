# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
"""Bid / Product readiness: BOM–supply alignment for Tender and Sales Order."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today

from pepl_os.pepl_os.api.inventory_intelligence import (
    get_on_order_position,
    get_open_mr_position,
    get_stock_position,
)

ACTIVE_TENDER_STATUSES = ["Active Bid", "Submitted"]

_COMPONENT_RANK = {"green": 0, "yellow": 1, "red": 2}


def _item_has_is_product():
    return frappe.db.has_column("Item", "is_product")


def _get_item_is_product(item_code):
    if not item_code or not _item_has_is_product():
        return 0
    return frappe.db.get_value("Item", item_code, "is_product") or 0


def _lead_time_days(item_code):
    if not item_code:
        return 14
    lt = frappe.db.get_value("Item", item_code, "lead_time_days")
    return int(lt) if lt else 14


def _component_status(required_qty, in_stock, on_order, open_mr, remaining_days, lead_days):
    """Colour thresholds: full readiness uses stock + PO + open MR vs requirement."""
    total_supply = in_stock + on_order + open_mr
    shortfall = required_qty - total_supply

    if shortfall <= 0:
        return "green", shortfall

    # Critical path vs timing when still short after pipeline
    if remaining_days is None:
        remaining_days = -1
    eff_remain = max(0, int(remaining_days))

    if shortfall > 0 and lead_days <= eff_remain:
        return "yellow", shortfall
    return "red", shortfall


def _worst_component_status(statuses):
    best_rank = -1
    worst_label = "green"
    for s in statuses:
        if not s:
            continue
        r = _COMPONENT_RANK.get(s, 0)
        if r > best_rank:
            best_rank = r
            worst_label = s
    return worst_label


def _is_sub_assembly_cst_row(row, component_item):
    if row.get("component_product"):
        return True
    return bool(_get_item_is_product(component_item))


def _is_sub_assembly_bom_row(item_code):
    return bool(_get_item_is_product(item_code))


def _get_default_bom_name(finished_item):
    return frappe.db.get_value(
        "BOM",
        {"item": finished_item, "is_default": 1, "is_active": 1, "docstatus": 1},
        "name",
    )


def _accumulate_cst_demands(
    component_demands,
    line_qty,
    cst_doc,
):
    """Add exploded RM demand from PEPL CST Cost Sheet.components."""
    for row in cst_doc.components or []:
        ci = row.component_item
        if not ci:
            continue
        qpa = flt(row.quantity_per_assembly) or 0
        req = flt(line_qty) * qpa
        if req <= 0:
            continue
        component_demands[ci] += req


def _accumulate_bom_demands(component_demands, line_qty, bom_doc):
    bom_qty = flt(bom_doc.quantity) or 1
    scale = flt(line_qty) / bom_qty
    for bom_row in bom_doc.items or []:
        ic = bom_row.item_code
        if not ic:
            continue
        is_stock = frappe.db.get_value("Item", ic, "is_stock_item") or 0
        if not is_stock:
            continue
        req = flt(bom_row.qty) * scale
        if req <= 0:
            continue
        component_demands[ic] += req


def _explode_tender_line_demands(item_code, line_qty, linked_cost_sheet):
    """Aggregate RM quantities required by one tender line (explosion rules match readiness panel)."""
    demands = defaultdict(float)
    if not item_code or not _get_item_is_product(item_code):
        return demands

    used_cst = False
    if linked_cost_sheet:
        cst_doc = frappe.get_doc("PEPL CST Cost Sheet", linked_cost_sheet)
        rows = cst_doc.components or []
        if rows:
            _accumulate_cst_demands(demands, line_qty, cst_doc)
            used_cst = True

    if not used_cst:
        bom_name = _get_default_bom_name(item_code)
        if bom_name:
            bom_doc = frappe.get_doc("BOM", bom_name)
            _accumulate_bom_demands(demands, line_qty, bom_doc)

    return demands


def _explode_tender_document(tender_doc):
    """item_code -> total RM qty for whole tender."""
    total = defaultdict(float)
    for row in tender_doc.items or []:
        item_code = row.item
        line_qty = flt(row.quantity)
        lc = row.linked_cost_sheet
        part = _explode_tender_line_demands(item_code, line_qty, lc)
        for ic, q in part.items():
            total[ic] += q
    return total


def _calculate_contention(this_tender_name, this_components_map):
    """
    Compare this tender's RM demand vs other Active Bid / Submitted tenders.
    Returns list of contention dicts.
    """
    other_names = frappe.get_all(
        "PEPL Tender",
        filters={
            "status": ["in", ACTIVE_TENDER_STATUSES],
            "name": ["!=", this_tender_name],
        },
        pluck="name",
    )

    total_other_qty = defaultdict(float)
    tender_hits = defaultdict(set)

    for tname in other_names:
        try:
            odoc = frappe.get_doc("PEPL Tender", tname)
            line_map = _explode_tender_document(odoc)
            for ic, q in line_map.items():
                if q <= 0:
                    continue
                total_other_qty[ic] += q
                tender_hits[ic].add(tname)
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                title=f"Readiness contention: tender {tname}",
            )

    out = []
    for item_code, this_need in this_components_map.items():
        if this_need <= 0:
            continue
        other_need = total_other_qty.get(item_code, 0)
        supply = (
            get_stock_position(item_code)
            + get_on_order_position(item_code)
            + get_open_mr_position(item_code)
        )
        combined = flt(this_need) + flt(other_need)
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
        out.append(
            {
                "item_code": item_code,
                "item_name": item_name,
                "this_tender_demand": round(this_need, 6),
                "other_tenders_demand": round(other_need, 6),
                "other_tender_count": len(tender_hits.get(item_code, set())),
                "current_supply": round(supply, 6),
                "contention_status": "red" if combined > supply else "ok",
            }
        )

    out.sort(key=lambda r: r["item_code"])
    return out


def _cst_status_block(linked_cost_sheet):
    if not linked_cost_sheet:
        return {
            "has_cst": False,
            "cst_name": None,
            "cst_age_days": None,
            "is_stale": False,
        }
    exists = frappe.db.exists("PEPL CST Cost Sheet", linked_cost_sheet)
    if not exists:
        return {
            "has_cst": False,
            "cst_name": linked_cost_sheet,
            "cst_age_days": None,
            "is_stale": False,
        }
    modified = frappe.db.get_value("PEPL CST Cost Sheet", linked_cost_sheet, "modified")
    age = (
        date_diff(getdate(today()), getdate(modified))
        if modified
        else 0
    )
    stale = age > 60
    return {
        "has_cst": True,
        "cst_name": linked_cost_sheet,
        "cst_age_days": age,
        "is_stale": stale,
    }


def _remaining_days_tender(tender_doc):
    dl = tender_doc.bid_submission_deadline
    if not dl:
        return None
    try:
        return date_diff(getdate(dl), getdate(today()))
    except Exception:
        return None


def _remaining_days_so(so_doc):
    dd = so_doc.delivery_date
    if not dd:
        return None
    try:
        return date_diff(getdate(dd), getdate(today()))
    except Exception:
        return None


def _build_components_from_cst(line_qty, cst_doc, remaining_days):
    components = []
    statuses = []
    for row in cst_doc.components or []:
        ci = row.component_item
        if not ci:
            continue
        qpa = flt(row.quantity_per_assembly) or 0
        req = flt(line_qty) * qpa
        sub_assembly = _is_sub_assembly_cst_row(row, ci)

        in_stock = get_stock_position(ci)
        on_order = get_on_order_position(ci)
        open_mr = get_open_mr_position(ci)
        lead_days = _lead_time_days(ci)
        col, shortfall = _component_status(
            req, in_stock, on_order, open_mr, remaining_days, lead_days
        )
        statuses.append(col)
        components.append(
            {
                "item_code": ci,
                "item_name": frappe.db.get_value("Item", ci, "item_name") or ci,
                "required_qty": round(req, 6),
                "in_stock": round(in_stock, 6),
                "on_order": round(on_order, 6),
                "open_mr": round(open_mr, 6),
                "shortfall": round(max(0, shortfall), 6),
                "lead_time_days": lead_days,
                "status": col,
                "sub_assembly": bool(sub_assembly),
            }
        )
    return components, statuses


def _build_components_from_bom(line_qty, bom_doc, remaining_days):
    components = []
    statuses = []
    bom_qty = flt(bom_doc.quantity) or 1
    scale = flt(line_qty) / bom_qty

    for bom_row in bom_doc.items or []:
        ic = bom_row.item_code
        if not ic:
            continue
        is_stock = frappe.db.get_value("Item", ic, "is_stock_item") or 0
        if not is_stock:
            continue
        req = flt(bom_row.qty) * scale
        sub_assembly = _is_sub_assembly_bom_row(ic)

        in_stock = get_stock_position(ic)
        on_order = get_on_order_position(ic)
        open_mr = get_open_mr_position(ic)
        lead_days = _lead_time_days(ic)
        col, shortfall = _component_status(
            req, in_stock, on_order, open_mr, remaining_days, lead_days
        )
        statuses.append(col)
        components.append(
            {
                "item_code": ic,
                "item_name": frappe.db.get_value("Item", ic, "item_name") or ic,
                "required_qty": round(req, 6),
                "in_stock": round(in_stock, 6),
                "on_order": round(on_order, 6),
                "open_mr": round(open_mr, 6),
                "shortfall": round(max(0, shortfall), 6),
                "lead_time_days": lead_days,
                "status": col,
                "sub_assembly": bool(sub_assembly),
            }
        )
    return components, statuses


def _analyze_product_line(
    *,
    item_code,
    line_qty,
    linked_cost_sheet,
    remaining_days,
):
    """Single finished-good line (tender row.item or SO item_code)."""
    row_qty = flt(line_qty)
    result_base = {
        "item_code": item_code,
        "item_name": frappe.db.get_value("Item", item_code, "item_name") if item_code else None,
        "line_qty": row_qty,
        "is_product": False,
        "bom_source": None,
        "bom_name": None,
        "components": [],
        "product_status": "skipped",
        "cst_status": _cst_status_block(linked_cost_sheet),
    }

    if not item_code:
        result_base["product_status"] = "no_item"
        return result_base

    result_base["item_name"] = frappe.db.get_value("Item", item_code, "item_name") or item_code

    if not _get_item_is_product(item_code):
        return result_base

    result_base["is_product"] = True

    used_cst = False
    if linked_cost_sheet and frappe.db.exists("PEPL CST Cost Sheet", linked_cost_sheet):
        cst_doc = frappe.get_doc("PEPL CST Cost Sheet", linked_cost_sheet)
        if cst_doc.components:
            comps, sts = _build_components_from_cst(row_qty, cst_doc, remaining_days)
            result_base["bom_source"] = "CST"
            result_base["bom_name"] = linked_cost_sheet
            result_base["components"] = comps
            result_base["product_status"] = (
                _worst_component_status(sts) if sts else "no_bom"
            )
            used_cst = True

    if not used_cst:
        bom_name = _get_default_bom_name(item_code)
        if bom_name:
            bom_doc = frappe.get_doc("BOM", bom_name)
            comps, sts = _build_components_from_bom(row_qty, bom_doc, remaining_days)
            result_base["bom_source"] = "Item Default BOM"
            result_base["bom_name"] = bom_name
            result_base["components"] = comps
            result_base["product_status"] = (
                _worst_component_status(sts) if sts else "no_bom"
            )
        else:
            result_base["bom_source"] = "None"
            result_base["product_status"] = "no_bom"

    return result_base


@frappe.whitelist()
def get_tender_bid_readiness(tender_name):
    """Bid readiness for PEPL Tender: BOM/supply + contention + CST summary."""
    if not tender_name:
        frappe.throw(_("Tender name required"))

    tender = frappe.get_doc("PEPL Tender", tender_name)
    rem_days = _remaining_days_tender(tender)

    line_items = []

    total_cst_lines = 0
    stale_cst_lines = 0

    for row in tender.items or []:
        try:
            item_code = row.item
            lc = row.linked_cost_sheet
            analyzed = _analyze_product_line(
                item_code=item_code,
                line_qty=flt(row.quantity),
                linked_cost_sheet=lc,
                remaining_days=rem_days,
            )
            cs = analyzed.get("cst_status") or {}
            if cs.get("has_cst"):
                total_cst_lines += 1
                if cs.get("is_stale"):
                    stale_cst_lines += 1

            if not analyzed.get("is_product"):
                continue

            line_items.append(analyzed)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                title=f"Bid readiness line failed (Tender {tender_name})",
            )

    aggregate_components = _explode_tender_document(tender)
    contention_warnings = _calculate_contention(tender.name, dict(aggregate_components))

    return {
        "tender": {
            "name": tender.name,
            "status": tender.status,
            "customer": tender.customer,
        },
        "cst_summary": {
            "total_lines_with_cst": total_cst_lines,
            "total_lines_with_stale_cst": stale_cst_lines,
        },
        "line_items": line_items,
        "contention_warnings": contention_warnings,
    }


@frappe.whitelist()
def get_so_product_readiness(sales_order_name):
    """Product readiness for Sales Order (no contention / CST summary)."""
    if not sales_order_name:
        frappe.throw(_("Sales Order name required"))

    so = frappe.get_doc("Sales Order", sales_order_name)
    rem_days = _remaining_days_so(so)

    line_items = []

    for so_item in so.items or []:
        try:
            item_code = so_item.item_code
            analyzed = _analyze_product_line(
                item_code=item_code,
                line_qty=flt(so_item.qty),
                linked_cost_sheet=None,
                remaining_days=rem_days,
            )
            # SO panel hides CST fields — normalize block for frontend
            analyzed["cst_status"] = {
                "has_cst": False,
                "cst_name": None,
                "cst_age_days": None,
                "is_stale": False,
            }

            if not analyzed.get("is_product"):
                continue

            line_items.append(analyzed)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                title=f"Product readiness line failed (SO {sales_order_name})",
            )

    return {
        "sales_order": {"name": so.name, "status": so.status},
        "line_items": line_items,
    }
