"""
Sprint 1 dashboard render fix — direct child insert strategy.

PROBLEM
-------
Frappe v14+ Workspaces render Number Cards and Dashboard Charts
from TWO sources that must agree:
  1. The `content` field (layout JSON) — already correct
  2. The `number_cards` and `charts` child tables on the parent
     Workspace doc — missing on Sprint 1 dashboard workspaces

WHY DIRECT INSERT (NOT ws.save())
---------------------------------
Calling ws.save() runs full parent validation including:
  - mandatory parent fields (type, etc.) — already bit us once
  - _validate_links() on every Link / Dynamic Link across all
    child tables — bit us with orphan 'quotation-comparison'
  - custom Workspace controller validate logic
  - re-validation of OTHER child tables (links, shortcuts,
    roles, quick_lists, custom_blocks) any of which may have
    drift we don't know about

Child rows are independent DB rows in `tab<Child DocType>`
linked to parent via parent/parenttype/parentfield. Insert
them directly and parent validation is irrelevant.
"""
import frappe
import json


WORKSPACES = [
    "PCC Home",
    "PCC To Order",
    "PCC To Receive",
    "PCC Payments",
    "PCC Vendors",
]


def execute():
    card_child_dt, chart_child_dt = _resolve_child_doctypes()
    print(
        f"  Resolved child DocTypes: "
        f"cards='{card_child_dt}', charts='{chart_child_dt}'"
    )

    for ws_name in WORKSPACES:
        if not frappe.db.exists("Workspace", ws_name):
            print(f"  SKIP: Workspace '{ws_name}' not found")
            continue
        try:
            _link_workspace(ws_name, card_child_dt, chart_child_dt)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            print(f"  ERROR on {ws_name}: {type(e).__name__}: {e}")
            continue


def _resolve_child_doctypes():
    """Look up the actual child DocType names from Workspace meta."""
    meta = frappe.get_meta("Workspace")
    card_dt = None
    chart_dt = None
    for df in meta.fields:
        if df.fieldname == "number_cards" and df.fieldtype == "Table":
            card_dt = df.options
        elif df.fieldname == "charts" and df.fieldtype == "Table":
            chart_dt = df.options
    if not card_dt or not chart_dt:
        raise Exception(
            f"Could not resolve child DocTypes from Workspace meta "
            f"(number_cards={card_dt}, charts={chart_dt})"
        )
    return card_dt, chart_dt


def _link_workspace(ws_name, card_child_dt, chart_child_dt):
    content_str = frappe.db.get_value("Workspace", ws_name, "content") or "[]"

    try:
        content = json.loads(content_str)
    except Exception as e:
        print(f"  {ws_name}: FAILED to parse content JSON: {e}")
        return

    card_refs, chart_refs = _extract_refs(content)

    existing_cards = _existing_child_values(
        card_child_dt, ws_name, "number_cards", "number_card_name"
    )
    existing_charts = _existing_child_values(
        chart_child_dt, ws_name, "charts", "chart_name"
    )

    max_idx_cards = _max_idx(card_child_dt, ws_name, "number_cards")
    max_idx_charts = _max_idx(chart_child_dt, ws_name, "charts")

    added_cards, missing_cards = _insert_child_rows(
        child_doctype=card_child_dt,
        parent=ws_name,
        parentfield="number_cards",
        link_field="number_card_name",
        target_doctype="Number Card",
        refs=card_refs,
        existing=existing_cards,
        start_idx=max_idx_cards,
    )

    added_charts, missing_charts = _insert_child_rows(
        child_doctype=chart_child_dt,
        parent=ws_name,
        parentfield="charts",
        link_field="chart_name",
        target_doctype="Dashboard Chart",
        refs=chart_refs,
        existing=existing_charts,
        start_idx=max_idx_charts,
    )

    if added_cards or added_charts:
        # Bump parent's modified timestamp so frontend cache refetches.
        # Done via raw SQL to skip all controller logic.
        frappe.db.sql(
            "UPDATE `tabWorkspace` SET modified=%s WHERE name=%s",
            (frappe.utils.now(), ws_name),
        )

    print(f"  {ws_name}: +{added_cards} cards, +{added_charts} charts")
    if missing_cards:
        print(f"    MISSING CARDS: {missing_cards}")
    if missing_charts:
        print(f"    MISSING CHARTS: {missing_charts}")


def _extract_refs(content):
    """Parse workspace content JSON and pull out all card/chart names."""
    card_refs = []
    chart_refs = []
    for block in content:
        btype = block.get("type")
        data = block.get("data") or {}
        if btype == "number_card":
            if isinstance(data.get("number_cards"), list):
                for c in data["number_cards"]:
                    name = (c or {}).get("number_card_name")
                    if name:
                        card_refs.append(name)
            elif data.get("number_card_name"):
                card_refs.append(data["number_card_name"])
        elif btype == "chart":
            if data.get("chart_name"):
                chart_refs.append(data["chart_name"])
    return card_refs, chart_refs


def _existing_child_values(child_dt, parent, parentfield, link_field):
    """Return set of link-field values already linked to this workspace."""
    rows = frappe.db.sql(
        f"""
        SELECT `{link_field}`
        FROM `tab{child_dt}`
        WHERE parent=%s
          AND parenttype='Workspace'
          AND parentfield=%s
        """,
        (parent, parentfield),
    )
    return {r[0] for r in rows if r[0]}


def _max_idx(child_dt, parent, parentfield):
    result = frappe.db.sql(
        f"""
        SELECT COALESCE(MAX(idx), 0)
        FROM `tab{child_dt}`
        WHERE parent=%s
          AND parenttype='Workspace'
          AND parentfield=%s
        """,
        (parent, parentfield),
    )
    return int(result[0][0]) if result else 0


def _insert_child_rows(
    child_doctype,
    parent,
    parentfield,
    link_field,
    target_doctype,
    refs,
    existing,
    start_idx,
):
    """Insert one child row per ref. Per-row error handling."""
    added = 0
    missing = []
    next_idx = start_idx

    for name in refs:
        if name in existing:
            continue
        if not frappe.db.exists(target_doctype, name):
            missing.append(name)
            continue
        next_idx += 1
        try:
            row = frappe.get_doc({
                "doctype": child_doctype,
                "parent": parent,
                "parenttype": "Workspace",
                "parentfield": parentfield,
                "idx": next_idx,
                link_field: name,
                "label": name,
            })
            # Carpet-bomb the row insert with bypass flags.
            # We've already verified the link target exists.
            row.flags.ignore_links = True
            row.flags.ignore_permissions = True
            row.flags.ignore_validate = True
            row.insert(ignore_permissions=True)
            existing.add(name)
            added += 1
        except Exception as e:
            print(
                f"    FAILED to insert {child_doctype} for {name}: "
                f"{type(e).__name__}: {e}"
            )

    return added, missing
