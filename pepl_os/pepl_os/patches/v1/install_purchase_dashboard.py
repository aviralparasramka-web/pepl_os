"""
Patch: install_purchase_dashboard
Sprint 1 — Purchase Command Centre

Loads all Workspace, Number Card, and Dashboard Chart JSON fixtures
that live under pepl_os/pepl_os/{folder}/<slug>/<slug>.json.

Rules:
- ADDITIVE only — never overwrites a record that already exists.
- Skips any JSON file that does not pass basic validation.
- Idempotent: safe to re-run.
"""

import json
import os

import frappe


def execute():
    base_dir = os.path.dirname(  # patches/v1/
        os.path.dirname(          # patches/
            os.path.abspath(__file__)
        )
    )  # → pepl_os/pepl_os/pepl_os/

    folders = {
        "workspace": "Workspace",
        "number_card": "Number Card",
        "dashboard_chart": "Dashboard Chart",
        "report": "Report",
    }

    results = {"inserted": [], "skipped": [], "errors": []}

    for folder, doctype in folders.items():
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        for slug in sorted(os.listdir(folder_path)):
            slug_dir = os.path.join(folder_path, slug)
            if not os.path.isdir(slug_dir):
                continue

            # File name matches slug with .json extension
            json_file = os.path.join(slug_dir, f"{slug}.json")
            if not os.path.isfile(json_file):
                continue

            try:
                with open(json_file, encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception as exc:
                results["errors"].append(f"{json_file}: JSON parse error — {exc}")
                continue

            # Remove internal comment keys (not valid Frappe fields)
            data.pop("_comment", None)

            record_name = data.get("name")
            if not record_name:
                results["errors"].append(f"{json_file}: missing 'name' field — skipped")
                continue

            if frappe.db.exists(doctype, record_name):
                results["skipped"].append(f"{doctype}: {record_name}")
                continue

            try:
                doc = frappe.get_doc(data)
                doc.flags.ignore_permissions = True
                doc.flags.ignore_mandatory = True
                doc.insert()
                frappe.db.commit()
                results["inserted"].append(f"{doctype}: {record_name}")
            except Exception as exc:
                frappe.db.rollback()
                results["errors"].append(f"{doctype} '{record_name}': {exc}")

    # Summary log
    frappe.logger("install_purchase_dashboard").info(
        "install_purchase_dashboard patch complete — "
        f"inserted={len(results['inserted'])}, "
        f"skipped={len(results['skipped'])}, "
        f"errors={len(results['errors'])}"
    )
    if results["errors"]:
        frappe.logger("install_purchase_dashboard").warning(
            "Errors during install_purchase_dashboard:\n"
            + "\n".join(results["errors"])
        )
