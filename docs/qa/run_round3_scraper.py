"""Round-3 closure audit for S01/S02 using isolated temporary databases.

Runs every store separately before the combined run, records wall-clock time,
row/detail/image counts, and preserves redacted logs under docs/qa/round3.
No production database is modified.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round3"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import full_scraper as fs
from run_scraper_audit import fixture


STORES = ("advice", "jib", "ihavecpu")
ERROR_PATTERN = re.compile(
    r"(?:\b(?:http |detail |card )?err(?:or)?\b|traceback|exception|timed? ?out|rate.?limit|\b429\b)",
    re.IGNORECASE,
)
RETRY_PATTERN = re.compile(r"\b(?:retry|backoff|attempt\s+[2-9])\b", re.IGNORECASE)


def database_stats(path: Path, store: str | None = None) -> dict:
    conn = sqlite3.connect(path)
    stores = (store,) if store else STORES
    per_store = {}
    for name in stores:
        total = conn.execute(
            f"SELECT count(*) FROM products WHERE price_{name}>0"
        ).fetchone()[0]
        described = conn.execute(
            f"SELECT count(*) FROM products "
            f"WHERE price_{name}>0 AND coalesce(desc_{name},'')<>''"
        ).fetchone()[0]
        imaged = conn.execute(
            f"SELECT count(*) FROM products "
            f"WHERE price_{name}>0 AND coalesce(img_url,'')<>''"
        ).fetchone()[0]
        per_store[name] = {
            "products": total,
            "with_description": described,
            "with_image": imaged,
        }
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    return {"per_store": per_store, "integrity": integrity}


def assess(phase: str, stats: dict, error_count: int, completed: bool) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not completed:
        reasons.append("run did not return before its evidence-based deadline")
    if stats["integrity"] != "ok":
        reasons.append("SQLite integrity_check failed")
    for store, values in stats["per_store"].items():
        count = values["products"]
        if count == 0:
            reasons.append(f"{store}: zero products")
        # Round 2 explicitly describes 313/226 as partial baselines. Use them
        # to catch severe under-collection, not as an upper cap for a complete
        # multi-category run that can legitimately return more products.
        if phase == "S01" and store == "advice" and count < 156:
            reasons.append(f"advice: {count} below 50% of partial baseline 313")
        if phase == "S01" and store == "jib" and count < 113:
            reasons.append(f"jib: {count} below 50% of partial baseline 226")
        if phase == "S02" and values["with_description"] != count:
            reasons.append(
                f"{store}: descriptions {values['with_description']}/{count} incomplete"
            )
        if phase == "S02" and values["with_image"] != count:
            reasons.append(f"{store}: images {values['with_image']}/{count} incomplete")
    if error_count:
        reasons.append(f"log contains {error_count} handled error/rate-limit markers")
    if not reasons:
        return "Pass", []
    # A completed run with incomplete evidence is a test failure; an unfinished
    # deadline remains Blocked because the final data set cannot be assessed.
    return ("Fail" if completed else "Blocked"), reasons


async def run_case(
    phase: str,
    label: str,
    stores: list[str],
    pages: int,
    details: bool,
    deadline_seconds: int,
) -> dict:
    with tempfile.TemporaryDirectory(
        prefix=f"qa-{phase.lower()}-{label}-", ignore_cleanup_errors=True
    ) as temp:
        db_path = Path(temp) / "shop.db"
        conn = fixture(db_path)
        conn.close()
        fs.DB_PATH = str(db_path)
        log_path = OUT / f"{phase}-{label}.log"
        started = datetime.now().astimezone()
        start = time.perf_counter()
        completed = True
        exception = None
        with log_path.open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log):
            print(
                json.dumps(
                    {
                        "phase": phase,
                        "label": label,
                        "stores": stores,
                        "pages": pages,
                        "details": details,
                        "deadline_seconds": deadline_seconds,
                        "started_at": started.isoformat(timespec="seconds"),
                    },
                    ensure_ascii=False,
                )
            )
            try:
                await asyncio.wait_for(
                    fs.run_all(stores, pages, details), timeout=deadline_seconds
                )
            except TimeoutError:
                completed = False
                exception = "TimeoutError"
                print(f"QA_DEADLINE_EXCEEDED seconds={deadline_seconds}")
            except Exception as exc:  # evidence, not a silent pass
                completed = True
                exception = f"{type(exc).__name__}: {str(exc)[:200]}"
                print(f"QA_UNHANDLED_EXCEPTION type={type(exc).__name__}")

        elapsed = round(time.perf_counter() - start, 3)
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        error_count = len(ERROR_PATTERN.findall(log_text))
        retry_count = len(RETRY_PATTERN.findall(log_text))
        stats = database_stats(db_path, stores[0] if len(stores) == 1 else None)
        if exception and completed:
            error_count += 1
        status, reasons = assess(phase, stats, error_count, completed)
        if exception:
            reasons.insert(0, exception)
        result = {
            "phase": phase,
            "label": label,
            "stores": stores,
            "pages_per_category": pages,
            "fetch_details": details,
            "started_at": started.isoformat(timespec="seconds"),
            "elapsed_seconds": elapsed,
            "deadline_seconds": deadline_seconds,
            "exit_code": 0 if completed and exception is None else 1,
            "completed": completed and exception is None,
            "error_marker_count": error_count,
            "retry_marker_count": retry_count,
            "stats": stats,
            "status": status,
            "reasons": reasons,
            "log": str(log_path.relative_to(ROOT)),
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return result


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("S01", "S02"))
    args = parser.parse_args()
    phase = args.phase
    details = phase == "S02"
    pages = 2 if details else 3
    # Detail visits are intentionally much slower than listing collection.
    store_deadline = 1_800 if details else 600
    results = []
    for store in STORES:
        results.append(
            await run_case(phase, store, [store], pages, details, store_deadline)
        )

    observed = sum(item["elapsed_seconds"] for item in results)
    combined_deadline = max(
        300 if not details else 900,
        int(observed * 1.5 + 60),
    )
    results.append(
        await run_case(
            phase,
            "combined",
            list(STORES),
            pages,
            details,
            combined_deadline,
        )
    )

    summary = {
        "phase": phase,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observed_separate_elapsed_seconds": round(observed, 3),
        "combined_deadline_seconds": combined_deadline,
        "cases": results,
        "status": "Pass" if all(item["status"] == "Pass" for item in results) else "Fail",
    }
    result_path = OUT / f"{phase}-results.json"
    result_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(result_path), "status": summary["status"]}), flush=True)
    return 0 if summary["status"] == "Pass" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
