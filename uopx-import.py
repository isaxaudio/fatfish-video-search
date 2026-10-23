#!/usr/bin/env python3
"""
UOPX 2026 — Supabase Import
=============================
Upserts rows from uopx-am-assoc-import.csv into Supabase public.videos.
Matches on student_id (upsert: update if exists, insert if new).

Usage:
  python3 uopx-import.py                       # live upsert
  python3 uopx-import.py --dry-run             # preview only
  python3 uopx-import.py --hide-wgu            # hide WGU test rows only
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
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

INPUT_FILE = "uopx-am-assoc-import.csv"

# Columns to insert (search_name is generated — omit it)
INSERT_COLUMNS = [
    "student_id", "student_name", "first_name", "last_name",
    "school_name", "event_name", "event_year", "degree_name",
    "thumbnail_url", "smugmug_url", "download_url", "video_file_url",
    "status", "is_active",
]


def sb_request(method, path, body=None, extra_headers=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"[]"), None
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        return None, f"HTTP {e.code}: {body_txt}"


def hide_wgu_rows():
    print("Hiding WGU test rows...")
    resp, err = sb_request(
        "PATCH",
        "videos?school_name=eq.WGU",
        body={"status": "hidden", "is_active": False},
        extra_headers={"Prefer": "return=representation"},
    )
    if err:
        print(f"  ERROR: {err}")
    else:
        print(f"  Updated {len(resp or [])} WGU row(s) → status=hidden, is_active=false")


def load_rows(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {}
            for col in INSERT_COLUMNS:
                val = row.get(col, "")
                # Type coercions
                if col == "event_year":
                    try:
                        record[col] = int(val)
                    except (ValueError, TypeError):
                        record[col] = None
                elif col == "is_active":
                    record[col] = val.lower() in ("true", "1", "yes")
                else:
                    record[col] = val if val != "" else None
            rows.append(record)
    return rows


def upsert_batch(rows, dry_run=False):
    if dry_run:
        print(f"\n[DRY RUN] Would upsert {len(rows)} rows")
        for r in rows[:3]:
            print(f"  {r['student_id']} | {r['student_name']}")
        if len(rows) > 3:
            print(f"  ... and {len(rows) - 3} more")
        return

    # Supabase upsert: POST with Prefer=resolution=merge-duplicates, on_conflict=student_id
    BATCH = 50
    ok, errors = 0, 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        resp, err = sb_request(
            "POST",
            "videos?on_conflict=student_id",
            body=chunk,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=representation"},
        )
        if err:
            print(f"  BATCH {i // BATCH + 1} ERROR: {err}")
            errors += len(chunk)
        else:
            ok += len(resp or [])
            print(f"  Batch {i // BATCH + 1}: {len(resp or [])} rows upserted")

    print(f"\n{'─' * 50}")
    print(f"  OK:     {ok}")
    print(f"  Errors: {errors}")
    print(f"{'─' * 50}\n")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args

    if "--hide-wgu" in args:
        hide_wgu_rows()
        return

    print(f"\nUOPX 2026 — Supabase Import")
    print(f"{'─' * 50}\n")

    # Hide WGU rows first (non-destructive — just sets status)
    hide_wgu_rows()
    print()

    print(f"Loading: {INPUT_FILE}")
    rows = load_rows(INPUT_FILE)
    print(f"  Rows to upsert: {len(rows)}")
    print()

    upsert_batch(rows, dry_run=dry_run)

    if not dry_run:
        print(f"Done. Set is_active=true in Supabase to make rows searchable.")
        print(f"  SQL: UPDATE public.videos SET is_active=true, status='live'")
        print(f"       WHERE student_id LIKE 'UOPX-AM-ASSOC-%';\n")


if __name__ == "__main__":
    main()
