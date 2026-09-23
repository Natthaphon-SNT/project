"""Capture regression evidence for round-4 backend/JWT changes."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round4"
OUT.mkdir(exist_ok=True)


def run(label: str, command: list[str]) -> dict:
    started = datetime.now().astimezone()
    start = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.perf_counter() - start, 3)
    text = completed.stdout + completed.stderr
    log_path = OUT / f"{label}.log"
    log_path.write_text(text, encoding="utf-8")
    return {
        "command": command,
        "started_at": started.isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed,
        "exit_code": completed.returncode,
        "log": str(log_path.relative_to(ROOT)),
        "output_has_hmac_key_length_warning": "key length is 20 bytes" in text,
    }


def main() -> int:
    python = str(ROOT / "venv" / "Scripts" / "python.exe")
    backend = run(
        "backend-tests",
        [python, "-B", "-m", "unittest", "discover", "-s", "backend", "-v"],
    )
    match = re.search(r"Ran (\d+) tests", (OUT / "backend-tests.log").read_text(encoding="utf-8"))
    skipped = re.search(r"skipped=(\d+)", (OUT / "backend-tests.log").read_text(encoding="utf-8"))
    backend["tests"] = int(match.group(1)) if match else None
    backend["skipped"] = int(skipped.group(1)) if skipped else 0
    backend["passed"] = (
        backend["tests"] - backend["skipped"] if backend["tests"] is not None else None
    )
    backend["status"] = "Pass" if backend["exit_code"] == 0 else "Fail"

    api = run("api-audit", [python, "-B", "docs/qa/run_api_audit.py"])
    try:
        summary = json.loads((OUT / "api-audit.log").read_text(encoding="utf-8").splitlines()[-1])
    except (ValueError, IndexError):
        summary = {}
    api.update(summary)
    api["status"] = "Pass" if api["exit_code"] == 0 and summary.get("fail") == 0 else "Fail"

    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "backend": backend,
        "api_audit": api,
        "round3_frontend_evidence_reused": {
            "reason": "round-4 prompt says production build/Angular/browser smoke already passed and frontend was unchanged",
            "angular_tests": "14/14 Pass",
            "production_build": "exit 0",
            "browser_smoke": "33 Pass, 1 non-target Blocked",
        },
    }
    result["status"] = (
        "Pass" if backend["status"] == api["status"] == "Pass" else "Fail"
    )
    path = OUT / "regression-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(path), "status": result["status"]}))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
