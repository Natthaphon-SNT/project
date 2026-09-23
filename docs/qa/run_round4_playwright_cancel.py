"""Repeat cancellation with real Playwright pages and capture shutdown errors."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round4"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))
import full_scraper as fs


async def main() -> int:
    loop = asyncio.get_running_loop()
    captured: list[str] = []
    previous = loop.get_exception_handler()

    def handler(_loop, context):
        captured.append(str(context.get("exception") or context.get("message") or ""))

    loop.set_exception_handler(handler)
    try:
        with tempfile.TemporaryDirectory(prefix="round4-playwright-cancel-") as temporary:
            conn = sqlite3.connect(Path(temporary) / "state.db")
            conn.execute("CREATE TABLE products (product_id TEXT PRIMARY KEY)")
            fs.setup_db(conn)
            items = [
                {
                    "url": f"data:text/html,<main id='spec'>specification item {n}</main>",
                    "name": f"item {n}", "category": "CPU",
                }
                for n in range(8)
            ]

            async def slow_fetch(page, url, *_args, **_kwargs):
                await page.goto(url)
                await asyncio.sleep(1)
                return "verified specification " * 3, ""

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context()
                with patch.object(fs, "fetch_detail_page", side_effect=slow_fetch):
                    for _round in range(3):
                        task = asyncio.create_task(
                            fs.fetch_browser_detail_queue(
                                context, conn, "jib", items, concurrency=4
                            )
                        )
                        await asyncio.sleep(0.12)
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                await context.close()
                await browser.close()
            conn.close()
        await asyncio.sleep(0.2)
    finally:
        loop.set_exception_handler(previous)

    target_closed = sum("TargetClosedError" in message for message in captured)
    orphan_tasks = sum(
        "detail-" in task.get_name()
        for task in asyncio.all_tasks() if task is not asyncio.current_task()
    )
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "cancel_runs": 3,
        "real_playwright_pages": True,
        "captured_loop_exception_count": len(captured),
        "target_closed_error_count": target_closed,
        "orphan_detail_task_count": orphan_tasks,
        "status": "Pass" if not target_closed and not orphan_tasks else "Fail",
    }
    path = OUT / "B4-playwright-cancel-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(path), "status": result["status"]}))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
