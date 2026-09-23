"""Rotate the local JWT HMAC secret without printing the secret value.

Run this only in an announced deployment window.  Every token signed with the
previous value becomes invalid immediately after the backend restarts.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import secrets
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def replace_setting(text: str, name: str, value: str) -> str:
    lines = text.splitlines()
    replacement = f"{name}={value}"
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{name}="):
            lines[index] = replacement
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(replacement)
    return "\n".join(lines) + "\n"


def rotate(env_path: Path) -> dict[str, object]:
    env_path = env_path.resolve()
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    value = secrets.token_urlsafe(48)
    if len(value.encode("utf-8")) < 32:
        raise RuntimeError("generated JWT secret was unexpectedly short")
    updated = replace_setting(text, "JWT_SECRET", value)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".jwt-rotate-", dir=str(env_path.parent), text=True
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(updated)
        os.replace(temporary_name, env_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return {
        "status": "rotated",
        "environment_variable": "JWT_SECRET",
        "utf8_bytes": len(value.encode("utf-8")),
        "fingerprint_sha256_prefix": hashlib.sha256(value.encode()).hexdigest()[:12],
        "rotated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tokens_invalidated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply is required; rotation invalidates all existing JWTs")
    result = rotate(args.env_file)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
