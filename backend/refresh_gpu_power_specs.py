"""Refresh reviewed GPU references from manufacturer pages; preserve other specs.

Run from any directory: python backend/refresh_gpu_power_specs.py [--apply]
Only recognized desktop GPU families are updated. No prices/names/URLs are changed.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
import sqlite3
import httpx
from gpu_power_reference import REFERENCES, lookup_gpu_power


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def fetch_reference(reference):
    response = httpx.get(reference["url"], timeout=40, follow_redirects=True)
    response.raise_for_status()
    parser = PageText()
    parser.feed(response.text)
    text = " ".join(parser.parts)
    if not re.search(reference["pattern"], text, re.I):
        raise ValueError("Source no longer identifies the expected GPU")
    labels = {"tdp": r"(?:Total Graphics Power\s*\(W\)|Max\.? Power Consumption)",
              "recommended_psu_watt": r"Required System Power\s*\(W\)"}
    fields = {}
    for field, label in labels.items():
        if field not in reference:
            continue
        match = re.search(label + r"\s*:?\s*(?:\(?5\)?\s*)?(\d{2,4})(?:\s*W)?\b", text, re.I)
        if not match:
            raise ValueError(f"Missing {field} on {reference['url']}")
        value = int(match.group(1))
        if value != reference[field]:
            raise ValueError(f"Manufacturer changed {field} to {value}; review the reference before applying")
        fields[field] = value
    return fields


def refresh(db_path, apply=False):
    fetched = {r["model"]: fetch_reference(r) for r in REFERENCES}
    checked_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as db:
        rows = db.execute("SELECT product_id,p_name,specs FROM products WHERE category='GPU'").fetchall()
        updates = []
        for pid, name, specs in rows:
            reference = lookup_gpu_power(name)
            if not reference:
                continue
            fields = fetched[reference["model"]]
            original = re.sub(r"\n?\[Verified GPU power\].*?\[/Verified GPU power\]", "", specs or "", flags=re.S).strip()
            lines = ["[Verified GPU power]"]
            labels = {"tdp": "Total Graphics Power (W)", "recommended_psu_watt": "Required System Power (W)"}
            lines.extend(f"{labels[k]}: {v} W" for k, v in fields.items())
            lines.extend([f"Source URL: {reference['url']}", f"Source model: {reference['model']}",
                          f"Source scope: {reference['scope']}", f"Source checked at: {checked_at}", "[/Verified GPU power]"])
            updates.append(((original + "\n" + "\n".join(lines)).strip(), pid))
            print(f"{pid}: {fields}")
        if apply and updates:
            backup = Path(db_path).with_name("shop.before-gpu-power-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")
            with sqlite3.connect(backup) as dest:
                db.backup(dest)
            db.executemany("UPDATE products SET specs=? WHERE product_id=?", updates)
            print(f"Updated {len(updates)} products. Backup: {backup}")
        else:
            print(f"Dry run: {len(updates)} products; use --apply to save")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db", default=str(Path(__file__).with_name("shop.db")))
    args = parser.parse_args()
    refresh(args.db, args.apply)
