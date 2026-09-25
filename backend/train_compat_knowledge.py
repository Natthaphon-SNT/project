"""Build deterministic compatibility knowledge from scraped product details.

This is deliberately a data-normalisation step rather than an LLM fine-tune:
the raw descriptions remain in ``desc_*``/``p_description`` while ``specs`` is
rewritten to small, auditable Key: Value facts with source URLs.

Usage from any directory:
    python backend/train_compat_knowledge.py          # dry-run
    python backend/train_compat_knowledge.py --apply  # update backend/shop.db
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import full_scraper as matcher
import spec_parser as spec_parser


DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")
STORES = ("advice", "jib", "ihavecpu")
COMPAT_CATEGORIES = {
    "CPU", "Mainboard", "RAM", "GPU", "PSU", "Case", "Air Cooler",
    "Liquid Cooler", "Cooler",
}
FIELD_LABELS = {
    "socket": "Socket",
    "sockets": "Supported Sockets",
    "ram_support": "Supported Memory",
    "ddr_gen": "Memory Type",
    "tdp": "TDP",
    "recommended_psu_watt": "Recommended PSU",
    "power_connectors": "Power Connectors",
    "watt": "Wattage",
    "form_factor": "Form Factor",
    "supports_ff": "Supported Motherboard",
    "rating_watt": "Cooler TDP",
    "height_mm": "Max Cooler Height",
}
INVALID_DETAIL_MARKERS = (
    "เราใช้คุกกี้", "การใช้คุกกี้ที่มีความจำเป็น", "access denied",
    "captcha", "just a moment",
)


# Keep the markers in Unicode escapes so both Thai and English cookie blocks
# are rejected regardless of the source file's legacy encoding.
INVALID_DETAIL_MARKERS = (
    "\u0e04\u0e38\u0e01\u0e01\u0e35\u0e49", "\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e2a\u0e48\u0e27\u0e19\u0e1a\u0e38\u0e04\u0e04\u0e25",
    "cookie", "consent", "privacy policy", "access denied", "captcha", "just a moment",
)


def source_title(url: str) -> str:
    if not url:
        return ""
    slug = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
    return re.sub(r"[-_]+", " ", slug)


def usable_detail(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if len(compact) < 30:
        return False
    lower = compact.lower()
    return not any(marker in lower for marker in INVALID_DETAIL_MARKERS)


def contains_invalid_detail_marker(text: str) -> bool:
    """Identify a stale cookie/consent block without rejecting short specs."""
    lower = re.sub(r"\s+", " ", text or "").strip().lower()
    return bool(lower) and any(marker in lower for marker in INVALID_DETAIL_MARKERS)


def value_key(value):
    if isinstance(value, dict):
        return tuple(sorted(value.items()))
    if isinstance(value, list):
        return tuple(value)
    return value


def choose_fact(field: str, candidates: list[tuple[object, str, str]], name: str, category: str):
    """Resolve multiple store values conservatively and retain provenance."""
    if not candidates:
        return None
    identity = matcher.extract_category_identity(name, category)
    if field == "watt" and identity.get("watt"):
        matching = [item for item in candidates if item[0] == identity["watt"]]
        if matching:
            return matching[0]
        return None
    if field in ("tdp", "recommended_psu_watt"):
        return max(candidates, key=lambda item: int(item[0]))
    if field == "power_connectors":
        merged = {}
        for value, _store, _url in candidates:
            for connector, count in value.items():
                merged[connector] = max(merged.get(connector, 0), count)
        value, store, url = max(candidates, key=lambda item: len(item[0]))
        return merged, store, url
    if field == "sockets":
        merged = []
        for value, _store, _url in candidates:
            for socket in value:
                if socket not in merged:
                    merged.append(socket)
        _value, store, url = max(candidates, key=lambda item: len(item[0]))
        return merged, store, url
    counts = Counter(value_key(item[0]) for item in candidates)
    selected, count = counts.most_common(1)[0]
    # Conflicting single-source scalar claims are unsafe; let name parsing or
    # the UI's UNKNOWN state handle them instead of guessing.
    if len(counts) > 1 and count == 1:
        return None
    return next(item for item in candidates if value_key(item[0]) == selected)


def format_value(field: str, value) -> str:
    if field in ("tdp", "recommended_psu_watt", "watt", "rating_watt"):
        return f"{value} W"
    if field == "height_mm":
        return f"{value} mm"
    if field in ("ram_support", "supports_ff", "sockets"):
        return ", ".join(value)
    if field == "power_connectors":
        return ", ".join(f"{count} x {name}" for name, count in sorted(value.items()))
    return str(value)


def canonical_specs(facts: dict, old_specs: str) -> str:
    lines = ["[Normalized compatibility facts]"]
    for field in FIELD_LABELS:
        if field not in facts:
            continue
        value, store, url = facts[field]
        label = FIELD_LABELS[field]
        lines.append(f"{label}: {format_value(field, value)}")
        lines.append(f"{label} Source Store: {store}")
        if url:
            lines.append(f"{label} Source URL: {url}")
    lines.append(f"Normalized at: {datetime.now(timezone.utc).isoformat()}")
    lines.append("[/Normalized compatibility facts]")
    # Preserve manually reviewed manufacturer evidence added by the GPU power
    # refresh task. Raw retailer text remains in the description columns.
    verified = re.findall(
        r"\[Verified GPU power\].*?\[/Verified GPU power\]",
        old_specs or "", flags=re.S,
    )
    return "\n".join(lines + verified)


def collect_product_facts(row: sqlite3.Row):
    category = row["category"] or ""
    if category not in COMPAT_CATEGORIES:
        return {}, [], []
    candidates = defaultdict(list)
    rejected = []
    sources = []
    seen_text = set()
    for store in STORES:
        detail = row[f"desc_{store}"] or ""
        url = row[f"url_{store}"] or ""
        if not usable_detail(detail) or detail in seen_text:
            continue
        seen_text.add(detail)
        title = source_title(url)
        if title and matcher.has_identity_conflict(row["p_name"], title, category):
            rejected.append((store, url, "source identity conflicts with product name"))
            continue
        facts = spec_parser.extract_detail_facts(category, detail)
        if not facts:
            continue
        sources.append((store, url, facts))
        for field, value in facts.items():
            if field in FIELD_LABELS and value not in (None, "", [], {}):
                candidates[field].append((value, store, url))

    # Older rows may only have p_description. It is still safe when there is a
    # single product source and no store description duplicated above.
    fallback = row["p_description"] or ""
    if usable_detail(fallback) and fallback not in seen_text:
        urls = [(store, row[f"url_{store}"] or "") for store in STORES if row[f"url_{store}"]]
        if len(urls) == 1:
            store, url = urls[0]
            title = source_title(url)
            if not title or not matcher.has_identity_conflict(row["p_name"], title, category):
                facts = spec_parser.extract_detail_facts(category, fallback)
                sources.append((store, url, facts))
                for field, value in facts.items():
                    if field in FIELD_LABELS and value not in (None, "", [], {}):
                        candidates[field].append((value, store, url))
    chosen = {}
    for field, values in candidates.items():
        selected = choose_fact(field, values, row["p_name"], category)
        if selected:
            chosen[field] = selected
    return chosen, sources, rejected


def learn_gpu_model_facts(rows_with_facts):
    """Share a model fact only when two independent pages agree exactly."""
    grouped = defaultdict(lambda: defaultdict(list))
    for row, facts in rows_with_facts:
        if row["category"] != "GPU":
            continue
        model = matcher.extract_category_identity(row["p_name"], "GPU").get("model")
        if not model:
            continue
        for field in ("tdp", "recommended_psu_watt"):
            if field in facts:
                grouped[model][field].append(facts[field])
    learned = {}
    for model, fields in grouped.items():
        learned[model] = {}
        for field, values in fields.items():
            distinct_sources = {}
            for value, store, url in values:
                distinct_sources[url or f"{store}:{value}"] = (value, store, url)
            unique_values = {item[0] for item in distinct_sources.values()}
            if len(distinct_sources) >= 2 and len(unique_values) == 1:
                value, store, url = next(iter(distinct_sources.values()))
                learned[model][field] = (value, f"{store} (model consensus)", url)
    return learned


def repair_duplicate_urls(conn: sqlite3.Connection, apply: bool) -> int:
    """Detach a duplicated store URL only when exactly one row matches its identity."""
    repaired = 0
    for store in STORES:
        url_col, price_col, desc_col = f"url_{store}", f"price_{store}", f"desc_{store}"
        groups = conn.execute(
            f"SELECT {url_col} url FROM products WHERE COALESCE({url_col}, '') <> '' "
            f"GROUP BY {url_col} HAVING COUNT(*) > 1"
        ).fetchall()
        for group in groups:
            url = group["url"]
            title = source_title(url)
            attached = conn.execute(
                f"SELECT * FROM products WHERE {url_col} = ?", (url,)
            ).fetchall()
            compatible = [
                row for row in attached
                if matcher.is_same_product(
                    row["p_name"], row["category"] or "", title, row["category"] or ""
                )
            ]
            conflicting = [row for row in attached if row not in compatible]
            if len(compatible) != 1 or not conflicting:
                continue
            keep = compatible[0]
            for wrong in conflicting:
                repaired += 1
                if not apply:
                    continue
                wrong_desc = wrong[desc_col] or ""
                conn.execute(
                    f"UPDATE products SET {price_col}=0, {url_col}='', {desc_col}='', "
                    "p_description=CASE WHEN p_description=? THEN '' ELSE p_description END, "
                    "specs=CASE WHEN specs=? THEN '' ELSE specs END WHERE product_id=?",
                    (wrong_desc, wrong_desc, wrong["product_id"]),
                )
                remaining = conn.execute(
                    "SELECT price_advice,price_jib,price_ihavecpu FROM products WHERE product_id=?",
                    (wrong["product_id"],),
                ).fetchone()
                prices = [int(value) for value in remaining if value and value > 0]
                conn.execute(
                    "UPDATE price_history SET product_id=? WHERE product_id=? AND store=?",
                    (keep["product_id"], wrong["product_id"], store),
                )
                if prices:
                    conn.execute(
                        "UPDATE products SET p_price=? WHERE product_id=?",
                        (min(prices), wrong["product_id"]),
                    )
                else:
                    # This row existed only because the duplicated source was
                    # attached to the wrong identity. The source and history
                    # now live on the verified row, so retain no zero-price ghost.
                    conn.execute(
                        "DELETE FROM products WHERE product_id=?", (wrong["product_id"],)
                    )
    return repaired


def run(apply: bool) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    repaired = repair_duplicate_urls(conn, apply)
    rows = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    rows_with_facts = []
    rejected_count = 0
    for row in rows:
        facts, _sources, rejected = collect_product_facts(row)
        rows_with_facts.append((row, facts))
        rejected_count += len(rejected)
    learned = learn_gpu_model_facts(rows_with_facts)

    updated = 0
    field_counts = Counter()
    learned_fields = 0
    for row, facts in rows_with_facts:
        if row["category"] == "GPU":
            model = matcher.extract_category_identity(row["p_name"], "GPU").get("model")
            for field, sourced in learned.get(model, {}).items():
                if field not in facts:
                    facts[field] = sourced
                    learned_fields += 1
        if not facts:
            stale_specs = row["specs"] or ""
            specs_conflict = (
                bool(stale_specs) and row["category"] in COMPAT_CATEGORIES and
                matcher.has_identity_conflict(row["p_name"], stale_specs, row["category"])
            )
            if apply and (contains_invalid_detail_marker(stale_specs) or specs_conflict):
                verified = re.findall(
                    r"\[Verified GPU power\].*?\[/Verified GPU power\]",
                    stale_specs, flags=re.S,
                )
                conn.execute(
                    "UPDATE products SET specs=?, updated_at=? WHERE product_id=?",
                    ("\n".join(verified), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     row["product_id"]),
                )
                continue
            if apply and (row["specs"] or "").startswith("[Normalized compatibility facts]"):
                verified = re.findall(
                    r"\[Verified GPU power\].*?\[/Verified GPU power\]",
                    row["specs"] or "", flags=re.S,
                )
                conn.execute(
                    "UPDATE products SET specs=?, updated_at=? WHERE product_id=?",
                    ("\n".join(verified), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     row["product_id"]),
                )
            continue
        updated += 1
        field_counts.update(facts.keys())
        if apply:
            conn.execute(
                "UPDATE products SET specs=?, updated_at=? WHERE product_id=?",
                (canonical_specs(facts, row["specs"] or ""),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["product_id"]),
            )
    if apply:
        conn.commit()
    else:
        conn.rollback()
    conn.close()
    return {
        "mode": "apply" if apply else "dry-run",
        "products_scanned": len(rows),
        "products_normalized": updated,
        "fields": dict(sorted(field_counts.items())),
        "gpu_model_fields_learned": learned_fields,
        "conflicting_sources_rejected": rejected_count,
        "duplicate_source_attachments_repaired": repaired,
    }


def repair_psu_connector_facts(apply: bool) -> dict:
    """Normalize sourced PSU PCIe 8-pin facts missing from stored facts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM products WHERE category = 'PSU' ORDER BY product_id"
    ).fetchall()
    repaired = []
    try:
        for row in rows:
            current = spec_parser.parse_part(
                "PSU", row["p_name"] or "", row["specs"] or ""
            ).get("power_connectors") or {}
            if current.get("PCIe 8-pin", 0) and (
                row["specs"] or ""
            ).startswith("[Normalized compatibility facts]"):
                continue
            facts, _sources, _rejected = collect_product_facts(row)
            sourced = facts.get("power_connectors")
            if not sourced or not sourced[0].get("PCIe 8-pin", 0):
                continue
            repaired.append(row["product_id"])
            if apply:
                conn.execute(
                    "UPDATE products SET specs=?, updated_at=? WHERE product_id=?",
                    (canonical_specs(facts, row["specs"] or ""),
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["product_id"]),
                )
        if apply:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"mode": "apply" if apply else "dry-run",
            "psu_rows_scanned": len(rows), "psu_connector_facts_rebuilt": len(repaired),
            "product_ids": repaired}


def repair_case_form_factors(apply: bool) -> dict:
    """Refresh case motherboard support from the saved retailer specifications."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM products WHERE category = 'Case' ORDER BY product_id"
    ).fetchall()
    repaired = []
    try:
        for row in rows:
            facts, _sources, _rejected = collect_product_facts(row)
            sourced = facts.get("supports_ff")
            if not sourced:
                continue
            current = spec_parser.parse_part(
                "Case", row["p_name"] or "", row["specs"] or ""
            ).get("supports_ff") or []
            if current == sourced[0]:
                continue
            repaired.append(row["product_id"])
            if apply:
                conn.execute(
                    "UPDATE products SET specs=?, updated_at=? WHERE product_id=?",
                    (canonical_specs(facts, row["specs"] or ""),
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["product_id"]),
                )
        if apply:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"mode": "apply" if apply else "dry-run",
            "case_rows_scanned": len(rows), "case_form_factors_rebuilt": len(repaired),
            "product_ids": repaired}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write normalized facts to shop.db")
    parser.add_argument("--repair-psu-connectors", action="store_true",
                        help="normalize PSU rows with PCIe 8-pin facts missing from stored facts")
    parser.add_argument("--repair-case-form-factors", action="store_true",
                        help="refresh case motherboard support from saved retailer details")
    args = parser.parse_args()
    if args.repair_psu_connectors:
        result = repair_psu_connector_facts(args.apply)
    elif args.repair_case_form_factors:
        result = repair_case_form_factors(args.apply)
    else:
        result = run(args.apply)
    for key, value in result.items():
        print(f"{key}: {value}")
