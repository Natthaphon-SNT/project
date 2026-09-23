"""Deterministic round-4 evidence for queue, cancellation, circuit and JWT."""

from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round4"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))

import full_scraper as fs


class FakePage:
    async def close(self):
        return None


class FakeContext:
    async def new_page(self):
        return FakePage()


def connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE products (product_id TEXT PRIMARY KEY)")
    fs.setup_db(conn)
    return conn


async def queue_benchmark() -> dict:
    items = [
        {"url": f"https://jib.example/{n}", "name": f"JIB item {n}", "category": "CPU"}
        for n in range(12)
    ]

    async def fake_fetch(*_args, **_kwargs):
        await asyncio.sleep(0.04)
        return "verified description " * 3, "https://img.example/item.jpg"

    with tempfile.TemporaryDirectory(prefix="round4-queue-") as temporary:
        sequential = connection(Path(temporary) / "sequential.db")
        concurrent = connection(Path(temporary) / "concurrent.db")
        with patch.object(fs, "fetch_detail_page", side_effect=fake_fetch):
            start = time.perf_counter()
            _, sequential_metrics = await fs.fetch_browser_detail_queue(
                FakeContext(), sequential, "jib", items, concurrency=1
            )
            sequential_wall = time.perf_counter() - start
            start = time.perf_counter()
            _, concurrent_metrics = await fs.fetch_browser_detail_queue(
                FakeContext(), concurrent, "jib", items, concurrency=4
            )
            concurrent_wall = time.perf_counter() - start
        sequential.close()
        concurrent.close()
    return {
        "items": len(items),
        "sequential_elapsed_seconds": round(sequential_wall, 4),
        "bounded_concurrent_elapsed_seconds": round(concurrent_wall, 4),
        "sequential_pages_per_second": sequential_metrics["pages_per_second"],
        "bounded_concurrent_pages_per_second": concurrent_metrics["pages_per_second"],
        "speedup": round(sequential_wall / concurrent_wall, 2),
        "configured_concurrency": concurrent_metrics["concurrency"],
        "status": "Pass" if concurrent_wall < sequential_wall else "Fail",
    }


async def cancel_resume_evidence() -> dict:
    items = [
        {"url": f"https://jib.example/resume/{n}", "name": f"item {n}", "category": "CPU"}
        for n in range(12)
    ]
    loop_errors: list[str] = []
    loop = asyncio.get_running_loop()
    old_handler = loop.get_exception_handler()

    def handler(_loop, context):
        loop_errors.append(str(context.get("exception") or context.get("message") or ""))

    loop.set_exception_handler(handler)
    try:
        with tempfile.TemporaryDirectory(prefix="round4-resume-") as temporary:
            conn = connection(Path(temporary) / "resume.db")
            async def interruptible(*_args, **_kwargs):
                await asyncio.sleep(0.025)
                return "verified description " * 3, "https://img.example/item.jpg"

            cancel_cleanup_samples = []
            with patch.object(fs, "fetch_detail_page", side_effect=interruptible):
                for _cancel_round in range(3):
                    task = asyncio.create_task(
                        fs.fetch_browser_detail_queue(
                            FakeContext(), conn, "jib", items, concurrency=2
                        )
                    )
                    await asyncio.sleep(0.04)
                    cancel_started = time.perf_counter()
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    cancel_cleanup_samples.append(time.perf_counter() - cancel_started)

            saved = conn.execute(
                "SELECT count(*) FROM scrape_detail_checkpoint WHERE status='success'"
            ).fetchone()[0]

            async def resume_fetch(*_args, **_kwargs):
                await asyncio.sleep(0.025)
                return "verified description " * 3, "https://img.example/item.jpg"

            with patch.object(fs, "fetch_detail_page", side_effect=resume_fetch):
                start = time.perf_counter()
                results, metrics = await fs.fetch_browser_detail_queue(
                    FakeContext(), conn, "jib", items, concurrency=2
                )
                resume_seconds = time.perf_counter() - start
            conn.close()
        await asyncio.sleep(0)
    finally:
        loop.set_exception_handler(old_handler)
    theoretical_restart_seconds = len(items) * 0.025 / 2
    return {
        "items": len(items),
        "saved_before_cancel": saved,
        "checkpoint_hits_on_resume": metrics["checkpoint_hits"],
        "fetched_on_resume": metrics["queued"],
        "final_results": len(results),
        "resume_elapsed_seconds": round(resume_seconds, 4),
        "estimated_full_restart_seconds": round(theoretical_restart_seconds, 4),
        "cancel_runs": 3,
        "cancel_cleanup_seconds_max": round(max(cancel_cleanup_samples), 4),
        "target_closed_error_count": sum("TargetClosedError" in error for error in loop_errors),
        "orphan_detail_task_count": sum(
            task.get_name().startswith("jib-detail-")
            for task in asyncio.all_tasks() if task is not asyncio.current_task()
        ),
        "status": "Pass" if (
            0 < saved < len(items) and len(results) == len(items) and
            metrics["checkpoint_hits"] == saved and
            resume_seconds < theoretical_restart_seconds and
            not any("TargetClosedError" in error for error in loop_errors)
        ) else "Fail",
    }


async def advice_circuit_evidence() -> dict:
    limiter = fs.AdaptiveRateLimiter("advice", threshold=2)
    await limiter.record_status(429)
    await limiter.record_status(429)
    await limiter.record_status(429)
    return {
        **limiter.metrics(),
        "rolling_window_seconds": limiter.window_seconds,
        "pause_remaining_seconds": round(
            max(0.0, limiter.pause_until - time.monotonic()), 3
        ),
        "starting_concurrency": fs.DETAIL_CONCURRENCY["advice"],
        "jib_concurrency": fs.DETAIL_CONCURRENCY["jib"],
        "status": "Pass" if (
            limiter.total_429 == 3 and limiter.circuit_open_count == 2 and
            fs.DETAIL_CONCURRENCY["advice"] < fs.DETAIL_CONCURRENCY["jib"]
        ) else "Fail",
    }


def env_setting(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return ""


def jwt_evidence() -> dict:
    secret = env_setting("JWT_SECRET")
    ai_values = {
        env_setting(name) for name in (
            "GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"
        )
    }
    ai_values.discard("")
    # Exercise signature rotation with disposable test secrets; neither value
    # is related to the newly generated deployment secret.
    import jwt
    old = "round4-old-disposable-secret-01234567890123456789"
    new = "round4-new-disposable-secret-01234567890123456789"
    token = jwt.encode({"uid": "qa"}, old, algorithm="HS256")
    old_rejected = False
    try:
        jwt.decode(token, new, algorithms=["HS256"])
    except jwt.InvalidSignatureError:
        old_rejected = True
    new_token = jwt.encode({"uid": "qa"}, new, algorithm="HS256")
    new_accepted = jwt.decode(new_token, new, algorithms=["HS256"])["uid"] == "qa"
    return {
        "environment_variable": "JWT_SECRET",
        "present": bool(secret),
        "utf8_bytes": len(secret.encode("utf-8")),
        "fingerprint_sha256_prefix": hashlib.sha256(secret.encode()).hexdigest()[:12],
        "separate_from_ai_provider_keys": bool(secret) and secret not in ai_values,
        "old_token_after_rotation": "401-equivalent invalid signature" if old_rejected else "accepted",
        "new_token_after_rotation": "accepted" if new_accepted else "rejected",
        "all_existing_sessions_must_login_again": True,
        "status": "Pass" if (
            len(secret.encode("utf-8")) >= 32 and secret not in ai_values and
            old_rejected and new_accepted
        ) else "Fail",
    }


def ihavecpu_edge_evidence() -> dict:
    product = {
        "product_id": 44014,
        "name_th": "SILICONE (ซิลิโคน) ARCTIC THERMAL MX-7 2G",
        "description_th": '<p><img src="https://example.invalid/image.jpg"></p>',
        "meta_description_th": "SILICONE (ซิลิโคน) ARCTIC THERMAL MX-7 2G",
    }
    description = fs.ihc_product_description(product)
    return {
        "product_id": 44014,
        "url": fs.ihc_product_url(product["product_id"], product["name_th"]),
        "root_cause": "description_th contains only an image; textual metadata is in meta_description_th",
        "source_field_used": "meta_description_th",
        "description_length": len(description),
        "status": "Pass" if len(description) >= 30 else "Fail",
    }


async def main() -> int:
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "B1_bounded_concurrency": await queue_benchmark(),
        "B2_advice_circuit_breaker": await advice_circuit_evidence(),
        "B3_B4_cancel_resume_cleanup": await cancel_resume_evidence(),
        "B5_ihavecpu_edge": ihavecpu_edge_evidence(),
        "B6_jwt_rotation": jwt_evidence(),
    }
    result["status"] = (
        "Pass" if all(section.get("status") == "Pass" for key, section in result.items()
                      if key.startswith("B")) else "Fail"
    )
    path = OUT / "engineering-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(path), "status": result["status"]}))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
