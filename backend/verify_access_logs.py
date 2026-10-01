"""Run live Supabase checks without printing keys or request/response content."""

import argparse
import getpass
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import uuid

from dotenv import load_dotenv
import httpx


def verify(client, base, service_key, anon_key, api_base=None):
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path):
        raise RuntimeError("SUPABASE_URL must be an HTTPS project origin")
    if not service_key or not anon_key:
        raise RuntimeError("Both service_role and anon keys are required for verification")
    service = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    anon = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    endpoint = base + "/rest/v1/access_logs"
    # A denied request with an invalid key does not prove table permissions.
    if client.get(base + "/auth/v1/settings", headers=anon).status_code != 200:
        raise RuntimeError("Anon key validity check failed; no access-control conclusion")
    if client.get(endpoint, headers=service, params={"select": "id", "limit": "1"}).status_code != 200:
        raise RuntimeError("Service-role table read failed; verify migration and backend key")
    read = client.get(endpoint, headers=anon, params={"select": "id", "limit": "1"})
    write = client.post(endpoint, headers={**anon, "Prefer": "return=minimal"}, json={
        "method": "POST", "path": "/api/auth/anon-permission-test", "status": 401,
        "ip": "203.0.113.100", "user_agent": "anon-permission-test", "user_id": None,
    })
    if read.status_code not in (401, 403) or write.status_code not in (401, 403):
        raise RuntimeError("Anon access is not denied; review privileges and RLS immediately")
    print("PASS: valid anon key cannot read/write access_logs; service_role can read")
    if not api_base:
        return
    parsed_api = urlsplit(api_base)
    if (parsed_api.scheme not in ("http", "https")
            or parsed_api.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed_api.username or parsed_api.password or parsed_api.query
            or parsed_api.fragment or parsed_api.path):
        raise RuntimeError("--api-base must be a local backend origin")
    marker = "AccessAudit/" + uuid.uuid4().hex
    headers = {"User-Agent": marker}
    responses = [
        client.post(api_base + "/api/login", headers=headers, json={
            "email": uuid.uuid4().hex + "@example.invalid", "password": "synthetic-wrong-password",
        }),
        client.get(api_base + "/api/admin/users", headers=headers),
    ]
    if any(response.status_code != 401 for response in responses):
        raise RuntimeError("Local login/admin did not return expected 401")
    client.get(api_base + "/api/products", headers=headers)
    client.get(api_base + "/products", headers=headers)
    deadline = time.monotonic() + 8
    rows = []
    while time.monotonic() < deadline:
        response = client.get(endpoint, headers=service, params={
            "select": "path,status,ip,user_agent", "user_agent": "eq." + marker,
        })
        if response.status_code != 200:
            raise RuntimeError("Cannot read verification rows with service_role")
        rows = response.json()
        if len(rows) >= 2:
            break
        time.sleep(0.2)
    expected = sorted([("/api/login", 401), ("/api/admin/users", 401)])
    if sorted((row["path"], row["status"]) for row in rows) != expected:
        raise RuntimeError("Expected login/admin rows missing, or an excluded path was recorded")
    if any(not row["ip"] or row["user_agent"] != marker for row in rows):
        raise RuntimeError("IP/User-Agent verification failed")
    print("PASS: real Supabase rows contain login/admin 401, IP and User-Agent; products excluded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", help="Optional local FastAPI origin, e.g. http://127.0.0.1:3000")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not base or not service_key:
        print("NOT VERIFIED: set SUPABASE_URL and SUPABASE_SERVICE_KEY privately")
        return 1
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or getpass.getpass("Anon key (hidden): ")
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            verify(client, base, service_key, anon_key, args.api_base)
    except (httpx.HTTPError, ValueError, KeyError):
        print("NOT VERIFIED: network or response validation failed; no secrets printed")
        return 1
    except RuntimeError as error:
        print("NOT VERIFIED: " + str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
