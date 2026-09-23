"""SEC01 evidence collector that never emits secret values."""

from __future__ import annotations

from datetime import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import httpx


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round3"
OUT.mkdir(exist_ok=True)
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{30,}")
SECRET_ASSIGNMENT = re.compile(
    r"(?im)^\s*[+-]?\s*(?:GOOGLE_API_KEY|OPENAI_API_KEY|OPENROUTER_API_KEY)\s*=\s*([^\s#]+)"
)
SKIP_DIRS = {".git", "node_modules", "dist", ".angular", "__pycache__"}
TEXT_EXTENSIONS = {
    ".py", ".ts", ".html", ".scss", ".css", ".json", ".md", ".txt",
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".env", ".bat", ".ps1",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("'\"").lower()
    return (
        not normalized
        or any(word in normalized for word in (
            "placeholder", "example", "dummy", "your_", "your-", "test_",
            "test-", "fake_", "fake-", "replace", "key-here", "os.getenv",
            "environ", "process.env", "<", ">", "${", "xxxxx",
        ))
    )


def scan_worktree(historical_key: str | None) -> dict:
    google_matches = 0
    nonempty_assignments = 0
    matched_files: list[dict] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != ".env":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        gm = GOOGLE_KEY.findall(text)
        assignments = [
            value for value in SECRET_ASSIGNMENT.findall(text)
            if value.strip().strip("'\"")
        ]
        if gm or assignments:
            relative = str(path.relative_to(ROOT))
            tracked = git("ls-files", "--error-unmatch", "--", relative).returncode == 0
            ignored = git("check-ignore", "--", relative).returncode == 0
            matched_files.append({
                "path": relative,
                "tracked": tracked,
                "ignored": ignored,
                "google_pattern_count": len(gm),
                "nonplaceholder_assignment_count": sum(
                    not is_placeholder(value) for value in assignments
                ),
                "contains_historical_key": bool(
                    historical_key and historical_key in gm
                ),
            })
        google_matches += len(gm)
        nonempty_assignments += len(assignments)
    return {
        "google_key_pattern_matches": google_matches,
        "nonempty_ai_secret_assignments": nonempty_assignments,
        "matched_file_count": len(matched_files),
        "matched_files": matched_files,
    }


def scan_history() -> tuple[dict, str | None]:
    history = git("log", "--all", "-p", "--no-textconv")
    values = GOOGLE_KEY.findall(history.stdout)
    unique = sorted(set(values))
    assignments = [
        value for value in SECRET_ASSIGNMENT.findall(history.stdout)
        if value.strip().strip("'\"")
    ]
    commits = git("log", "--all", "--format=%H", "--", ".env")
    return (
        {
            "full_history_exit_code": history.returncode,
            "full_history_error": history.stderr.strip()[:200],
            "commits_touching_env": len([x for x in commits.stdout.splitlines() if x]),
            "unique_google_key_pattern_matches": len(unique),
            "nonempty_ai_secret_assignment_occurrences": len(assignments),
            "contains_target_commit": any(
                commit.startswith("46c14ce") for commit in git(
                    "log", "--all", "--format=%h", "--", ".env"
                ).stdout.splitlines()
            ),
        },
        unique[0] if unique else None,
    )


def test_revocation(key: str | None) -> dict:
    if not key:
        return {"attempted": False, "reason": "historical Google key not found"}
    fingerprint = hashlib.sha256(key.encode()).hexdigest()[:12]
    try:
        response = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": key}, timeout=30, follow_redirects=True,
        )
        error_status = None
        error_message = ""
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                error_status = error.get("status")
                error_message = str(error.get("message") or "")
        except ValueError:
            pass
        invalid_signal = bool(
            error_status in {"API_KEY_INVALID", "PERMISSION_DENIED", "UNAUTHENTICATED"}
            or "API key not valid" in error_message
            or "API key was deleted" in error_message
        )
        return {
            "attempted": True,
            "key_sha256_prefix": fingerprint,
            "http_status": response.status_code,
            "google_error_status": error_status,
            "rejected": response.status_code in {400, 401, 403} and invalid_signal,
            "strict_prompt_status_met": response.status_code in {401, 403},
        }
    except Exception as exc:
        return {
            "attempted": True,
            "key_sha256_prefix": fingerprint,
            "network_error_type": type(exc).__name__,
            "rejected": False,
            "strict_prompt_status_met": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live-revocation-check",
        action="store_true",
        help="Transmit the historical key only with explicit owner authorization",
    )
    args = parser.parse_args()
    history, old_key = scan_history()
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "revision": git("rev-parse", "HEAD").stdout.strip(),
        "working_tree": scan_worktree(old_key),
        "git_history": history,
        "old_key_live_request": (
            test_revocation(old_key)
            if args.live_revocation_check
            else {
                "attempted": False,
                "reason": "credential transmission not authorized; offline scan only",
                "rejected": False,
                "strict_prompt_status_met": False,
            }
        ),
        "new_key_restrictions_verified": False,
        "new_key_restrictions_reason": (
            "requires authorized Google Cloud Console evidence; no new key is read or logged"
        ),
        "rotation_owner_and_timestamp_verified": False,
        "remote_history_rewrite_verified": False,
        "report_contains_secret_values": False,
    }
    path = OUT / "SEC01-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    safe_summary = {
        "result": str(path.relative_to(ROOT)),
        "working_tree": result["working_tree"],
        "git_history": history,
        "old_key_live_request": result["old_key_live_request"],
    }
    print(json.dumps(safe_summary, ensure_ascii=False))
    return 0 if result["old_key_live_request"].get("rejected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
