#!/usr/bin/env python3
"""
FF Video Platform — Bulk URL Updater
Usage:
  python3 bulk-update.py <csv-file>           # live run
  python3 bulk-update.py <csv-file> --dry-run # preview only, no writes

Matches ONLY on student_id. No name-based matching.

Required CSV column:
  student_id

Optional CSV columns (any combination):
  smugmug_url, download_url, thumbnail_url, video_file_url, status

status defaults to "uploaded" if not provided.
"""

import csv
import sys
import json
import urllib.request
import urllib.parse
import secrets_local as _secrets  # gitignored; holds API keys

SUPABASE_URL = "https://uqfxjqkwicoljgztkijw.supabase.co"
SUPABASE_KEY = _secrets.SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

URL_FIELDS = ("smugmug_url", "download_url", "thumbnail_url", "video_file_url")


def get_current(student_id):
    """Fetch current row from Supabase for diff."""
    params = urllib.parse.urlencode({
        "student_id": f"eq.{student_id}",
        "select": "student_id,student_name,smugmug_url,download_url,thumbnail_url,video_file_url,status"
    })
    url = f"{SUPABASE_URL}/rest/v1/videos?{params}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None, None
    except urllib.error.HTTPError as e:
        return None, e


def patch(student_id, payload):
    """Write update to Supabase."""
    params = urllib.parse.urlencode({"student_id": f"eq.{student_id}"})
    url = f"{SUPABASE_URL}/rest/v1/videos?{params}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=HEADERS,
        method="PATCH"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, e


def classify_error(e):
    """Return a human-readable error category from an HTTPError."""
    if e.code == 401:
        return "AUTH ERROR (401) — API key rejected"
    if e.code == 403:
        return "PERMISSION ERROR (403) — insufficient privileges"
    if e.code == 404:
        return "NOT FOUND (404) — endpoint missing"
    if e.code == 409:
        return "CONFLICT (409) — unique constraint violation"
    if e.code >= 500:
        return f"SERVER ERROR ({e.code}) — Supabase issue"
    try:
        body = e.read().decode()
    except Exception:
        body = "(no body)"
    return f"API ERROR ({e.code}): {body}"


def build_diff(current, payload):
    """Return list of 'field: old → new' strings for changed fields."""
    changes = []
    for field, new_val in payload.items():
        old_val = current.get(field, "") or ""
        if str(old_val) != str(new_val):
            old_display = old_val if old_val else "(empty)"
            changes.append(f"    {field}: {old_display} → {new_val}")
    return changes


def process(row, i, dry_run):
    sid = row.get("student_id", "").strip()

    if not sid:
        print(f"  [{i}] FAIL — student_id missing. Fix this row and rerun.")
        return "failed"

    # Build payload
    payload = {"status": row.get("status", "").strip() or "uploaded"}
    for field in URL_FIELDS:
        val = row.get(field, "").strip()
        if val:
            payload[field] = val

    # Fetch current record for diff and existence check
    current, err = get_current(sid)

    if err:
        print(f"  [{i}] {classify_error(err)} — {sid}")
        return "failed"

    if current is None:
        print(f"  [{i}] NOT FOUND — {sid} does not exist in Supabase. Check the ID.")
        return "not_found"

    name = current.get("student_name", "?")
    diff = build_diff(current, payload)

    if not diff:
        print(f"  [{i}] SKIP — {sid} | {name} | no changes detected")
        return "skipped"

    if dry_run:
        print(f"  [{i}] DRY RUN — {sid} | {name}")
        for line in diff:
            print(line)
        return "dry_run"

    # Live write
    result, err = patch(sid, payload)

    if err:
        print(f"  [{i}] {classify_error(err)} — {sid}")
        return "failed"

    print(f"  [{i}] OK — {sid} | {name}")
    for line in diff:
        print(line)

    return "ok"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 bulk-update.py <csv-file> [--dry-run]")
        sys.exit(1)

    csv_file = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    counts = {"ok": 0, "not_found": 0, "failed": 0, "skipped": 0, "dry_run": 0}

    mode = "DRY RUN — no writes will be made" if dry_run else "LIVE RUN"
    print(f"\nFF Video Platform — Bulk Updater")
    print(f"File: {csv_file}")
    print(f"Mode: {mode}\n")

    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames or "student_id" not in reader.fieldnames:
            print("ERROR: CSV must contain a 'student_id' column.")
            sys.exit(1)

        for i, row in enumerate(reader, start=1):
            outcome = process(row, i, dry_run)
            counts[outcome] += 1

    print(f"\n{'─' * 40}")
    if dry_run:
        print(f"  Would update: {counts['dry_run']}")
        print(f"  No changes:   {counts['skipped']}")
        print(f"  Not found:    {counts['not_found']}")
        print(f"  Failed:       {counts['failed']}")
        print(f"\n  Run without --dry-run to apply.")
    else:
        print(f"  Updated:      {counts['ok']}")
        print(f"  Skipped:      {counts['skipped']}  (no changes detected)")
        print(f"  Not found:    {counts['not_found']}  (check student_id values)")
        print(f"  Failed:       {counts['failed']}  (check errors above)")
    print(f"{'─' * 40}\n")


if __name__ == "__main__":
    main()
