"""
Sprint 1 dashboard render fix.

The workspace 'content' field correctly references Number Cards
and Dashboard Charts by name, but Frappe v14+ requires those
references to also be linked via the Workspace 'number_cards'
and 'charts' child tables. Without the child rows, layout blocks
render empty.

This patch parses each PEPL workspace's content JSON, extracts
every number_card_name and chart_name reference, validates the
target record exists, and appends a child table row if missing.
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
    for ws_name in WORKSPACES:
        if not frappe.db.exists("Workspace", ws_name):
            print(f"  SKIP: Workspace '{ws_name}' not found")
            continue
        _link_workspace(ws_name)
    frappe.db.commit()


def _link_workspace(ws_name):
    ws = frappe.get_doc("Workspace", ws_name)

    try:
        content = json.loads(ws.content or "[]")
    except Exception as e:
        print(f"  {ws_name}: FAILED to parse content JSON: {e}")
        return

    card_refs = []
    chart_refs = []
    for block in content:
        btype = block.get("type")
        data = block.get("data", {}) or {}
        if btype == "number_card":
            if isinstance(data.get("number_cards"), list):
                for c in data["number_cards"]:
                    name = c.get("number_card_name")
                    if name:
                        card_refs.append(name)
            elif data.get("number_card_name"):
                card_refs.append(data["number_card_name"])
        elif btype == "chart":
            if data.get("chart_name"):
                chart_refs.append(data["chart_name"])

    existing_cards = {
        r.number_card_name for r in (ws.get("number_cards") or [])
    }
    existing_charts = {
        r.chart_name for r in (ws.get("charts") or [])
    }

    added_cards = 0
    missing_cards = []
    for name in card_refs:
        if name in existing_cards:
            continue
        if not frappe.db.exists("Number Card", name):
            missing_cards.append(name)
            continue
        ws.append("number_cards", {
            "number_card_name": name,
            "label": name,
        })
        existing_cards.add(name)
        added_cards += 1

    added_charts = 0
    missing_charts = []
    for name in chart_refs:
        if name in existing_charts:
            continue
        if not frappe.db.exists("Dashboard Chart", name):
            missing_charts.append(name)
            continue
        ws.append("charts", {
            "chart_name": name,
            "label": name,
        })
        existing_charts.add(name)
        added_charts += 1

    if added_cards or added_charts:
        ws.save(ignore_permissions=True)

    print(f"  {ws_name}: +{added_cards} cards, +{added_charts} charts")
    if missing_cards:
        print(f"    MISSING CARDS: {missing_cards}")
    if missing_charts:
        print(f"    MISSING CHARTS: {missing_charts}")
