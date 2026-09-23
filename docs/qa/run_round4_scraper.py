"""Round-4 S02 verifier with persistent per-case checkpoint databases."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime
import gc
import json
from pathlib import Path
import re
import sqlite3
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round4"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import full_scraper as fs
from run_scraper_audit import fixture


STORES = ("advice", "jib", "ihavecpu")
CASE_STORES = {
    "advice": ["advice"],
    "jib": ["jib"],
    "ihavecpu": ["ihavecpu"],
    "combined": list(STORES),
}
DEADLINES = {"advice": 1800, "jib": 1800, "ihavecpu": 1800, "combined": 3600}
METRIC_PATTERN = re.compile(r"\[Detail queue metrics\]\s+(\{.*\})")


def database_stats(path: Path, stores: list[str]) -> dict:
    conn = sqlite3.connect(path)
    per_store = {}
    for store in stores:
        total = conn.execute(
            f"SELECT count(*) FROM products WHERE price_{store}>0"
        ).fetchone()[0]
        described = conn.execute(
            f"SELECT count(*) FROM products WHERE price_{store}>0 "
            f"AND length(trim(coalesce(desc_{store},'')))>=30"
        ).fetchone()[0]
        imaged = conn.execute(
            f"SELECT count(*) FROM products WHERE price_{store}>0 "
            "AND trim(coalesce(img_url,''))<>''"
        ).fetchone()[0]
        per_store[store] = {
            "products": total,
            "with_description": described,
            "with_image": imaged,
        }
    checkpoint = {
        row[0]: {"success": row[1], "failed": row[2], "attempts": row[3]}
        for row in conn.execute(
            "SELECT store, sum(status='success'), sum(status='failed'), sum(attempts) "
            "FROM scrape_detail_checkpoint GROUP BY store"
        ).fetchall()
    }
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    return {"per_store": per_store, "checkpoint": checkpoint, "integrity": integrity}


def parse_metrics(log_text: str) -> list[dict]:
    metrics = []
    for match in METRIC_PATTERN.finditer(log_text):
        try:
            metrics.append(json.loads(match.group(1)))
        except ValueError:
            pass
    return metrics


def assess(stats: dict, completed: bool, target_closed: int) -> tuple[str, list[str]]:
    reasons = []
    if not completed:
        reasons.append("run did not complete within the fixed round-4 deadline")
    if stats["integrity"] != "ok":
        reasons.append("SQLite integrity_check failed")
    if target_closed:
        reasons.append(f"TargetClosedError appeared {target_closed} time(s)")
    for store, values in stats["per_store"].items():
        total = values["products"]
        if not total:
            reasons.append(f"{store}: zero products")
        if values["with_description"] != total:
            reasons.append(
                f"{store}: descriptions {values['with_description']}/{total} incomplete"
            )
        if values["with_image"] != total:
            reasons.append(f"{store}: images {values['with_image']}/{total} incomplete")
    return ("Pass" if not reasons else ("Fail" if completed else "Blocked"), reasons)


async def run_case(label: str) -> dict:
    stores = CASE_STORES[label]
    db_path = OUT / f"S02-{label}.db"
    if not db_path.exists():
        conn = fixture(db_path)
        conn.close()
    before = database_stats(db_path, stores)
    fs.DB_PATH = str(db_path)
    log_path = OUT / f"S02-{label}.log"
    started = datetime.now().astimezone()
    start = time.perf_counter()
    exception = ""
    with (log_path.open("w", encoding="utf-8") as log,
          contextlib.redirect_stdout(log), contextlib.redirect_stderr(log)):
        print(json.dumps({
            "event": "run-start", "label": label, "stores": stores,
            "pages": 2, "details": True, "deadline_seconds": DEADLINES[label],
            "started_at": started.isoformat(timespec="seconds"),
            "checkpoint_before": before.get("checkpoint", {}),
        }, ensure_ascii=False))
        try:
            await asyncio.wait_for(
                fs.run_all(stores, pages=2, fetch_details=True),
                timeout=DEADLINES[label],
            )
        except TimeoutError:
            exception = "TimeoutError"
            print(f"QA_DEADLINE_EXCEEDED seconds={DEADLINES[label]}")
        except Exception as exc:
            exception = f"{type(exc).__name__}: {str(exc)[:200]}"
            print(f"QA_UNHANDLED_EXCEPTION {exception}")
        await asyncio.sleep(0.2)
        gc.collect()

    elapsed = round(time.perf_counter() - start, 3)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    metrics = parse_metrics(text)
    stats = database_stats(db_path, stores)
    target_closed = text.count("TargetClosedError")
    status, reasons = assess(stats, not exception, target_closed)
    if exception:
        reasons.insert(0, exception)
    queued = sum(item.get("queued", 0) for item in metrics)
    queue_elapsed = sum(item.get("elapsed_seconds", 0) for item in metrics)
    result = {
        "label": label,
        "stores": stores,
        "started_at": started.isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed,
        "deadline_seconds": DEADLINES[label],
        "exit_code": 0 if not exception else 1,
        "completed": not exception,
        "status": status,
        "reasons": reasons,
        "stats": stats,
        "detail_queue": {
            "queued": queued,
            "elapsed_seconds": round(queue_elapsed, 3),
            "pages_per_second": round(queued / queue_elapsed, 4) if queue_elapsed else 0,
            "metric_samples": metrics,
        },
        "http_429_marker_count": len(re.findall(r"(?:status=429|HTTP 429)", text, re.I)),
        "retry_marker_count": len(re.findall(r"\[(?:retry|circuit (?:open|wait))\]", text, re.I)),
        "target_closed_error_count": target_closed,
        "log": str(log_path.relative_to(ROOT)),
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def update_summary(result: dict) -> None:
    path = OUT / "S02-results.json"
    if path.exists():
        summary = json.loads(path.read_text(encoding="utf-8"))
    else:
        summary = {"phase": "S02-round4", "cases": {}, "history": {}}
    summary.setdefault("history", {})
    previous = summary.get("cases", {}).get(result["label"])
    if previous:
        summary["history"].setdefault(result["label"], []).append(previous)
    summary["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    summary["round3_baseline"] = {
        "jib_products_in_1800_seconds": 137,
        "jib_pages_per_second": round(137 / 1800, 4),
        "advice_http_429": 96,
        "advice_descriptions": "255/319",
        "ihavecpu_descriptions": "266/267",
    }
    summary["cases"][result["label"]] = result
    summary["status"] = (
        "Pass" if all(
            summary["cases"].get(label, {}).get("status") == "Pass"
            for label in CASE_STORES
        ) else "Incomplete"
    )
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=tuple(CASE_STORES) + ("all",))
    args = parser.parse_args()
    labels = list(CASE_STORES) if args.case == "all" else [args.case]
    exit_code = 0
    for label in labels:
        result = await run_case(label)
        update_summary(result)
        if result["status"] != "Pass":
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
