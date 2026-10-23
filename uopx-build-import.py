#!/usr/bin/env python3
"""
UOPX 2026 — AM Associates Supabase Import Builder
====================================================
1. Fetches all videos from SmugMug album pC2pK8 (AM - Associates)
2. Reads the master CSV
3. Multi-strategy name matching + manual overrides
4. Outputs uopx-am-assoc-import.csv ready for Supabase import

Usage:
  python3 uopx-build-import.py
  python3 uopx-build-import.py --sm-only    # just list SM filenames (debug)
  python3 uopx-build-import.py --csv-only   # just list CSV rows (debug)
"""

import sys
import csv
import json
import hmac
import hashlib
import base64
import time
import random
import string
import urllib.request
import urllib.parse
import re
import unicodedata

# ── Config ─────────────────────────────────────────────────────────────────
ALBUM_KEY   = "pC2pK8"   # AM - Associates
OUTPUT_FILE = "uopx-am-assoc-import.csv"
MASTER_CSV  = "/Users/isaacgonzalez/Downloads/Master List - UPDATED Master List.csv"

# Only include AM ceremony, Associates degree level
CEREMONY_FILTER = "AM"   # Ceremoney Time column
DEGREE_FILTER   = "1"    # Degree Level column (1 = Associates)

SCHOOL_NAME  = "University of Phoenix"
EVENT_NAME   = "AM Ceremony"
EVENT_YEAR   = 2026

# ── Manual filename → student_t overrides ──────────────────────────────────
# Key = SmugMug filename stem (without .mp4), normalized (lowercase, collapsed whitespace)
# Value = value of column "t" from master CSV
MANUAL_OVERRIDES_RAW = {
    "Bowden_Khyeasha":            "9058711226",   # Khyeasha Diane Bowden Fowler
    "Eldred-Culley-Nicole  A. Eldred": "9059136695",  # Nicole A. Eldred (double-space in filename)
    "Forte_Jessica M":            "9044242233",   # Jessica Marie Forte
    "Nelson_Lillian":             "9058319831",   # Lillian R. Picone Nelson
    "Stewart_Shkera":             "9058996667",   # Shakera Stewart (typo in filename)
    "Williams_Kimberly":          "9059065396",   # Kimberly Williams Aviza
}
# Normalize keys so whitespace variants don't break lookups
MANUAL_OVERRIDES = {re.sub(r"\s+", " ", k).strip(): v
                    for k, v in MANUAL_OVERRIDES_RAW.items()}
# ───────────────────────────────────────────────────────────────────────────

try:
    from smugmug_config import (
        SMUGMUG_API_KEY, SMUGMUG_API_SECRET,
        SMUGMUG_ACCESS_TOKEN, SMUGMUG_ACCESS_TOKEN_SECRET,
        SMUGMUG_USERNAME,
    )
except ImportError:
    print("ERROR: smugmug_config.py not found — run smugmug-auth.py first")
    sys.exit(1)

SMUGMUG_BASE = "https://www.smugmug.com/api/v2"


# ── OAuth helpers ──────────────────────────────────────────────────────────

def _nonce():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def _pct(s):
    return urllib.parse.quote(str(s), safe='')

def _oauth_header(method, base_url, query_params):
    op = {
        "oauth_consumer_key":     SMUGMUG_API_KEY,
        "oauth_nonce":            _nonce(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_version":          "1.0",
        "oauth_token":            SMUGMUG_ACCESS_TOKEN,
    }
    all_p     = {**query_params, **op}
    param_str = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(all_p.items()))
    base_str  = "&".join([method.upper(), _pct(base_url), _pct(param_str)])
    sk        = _pct(SMUGMUG_API_SECRET) + "&" + _pct(SMUGMUG_ACCESS_TOKEN_SECRET)
    sig       = base64.b64encode(
        hmac.new(sk.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    op["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{k}="{_pct(v)}"' for k, v in sorted(op.items()))


def smugmug_get(endpoint, params=None):
    base_url = f"{SMUGMUG_BASE}/{endpoint}"
    qp = {"_accept": "application/json"}
    if params:
        qp.update(params)
    headers = {
        "Accept":        "application/json",
        "Authorization": _oauth_header("GET", base_url, qp),
    }
    qs  = urllib.parse.urlencode(qp)
    req = urllib.request.Request(f"{base_url}?{qs}", headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── SmugMug fetching ────────────────────────────────────────────────────────

def fetch_sizes(image_key):
    try:
        d = smugmug_get(f"image/{image_key}!sizes")
        return d.get("Response", {}).get("ImageSizes", {})
    except Exception as e:
        print(f"    WARNING: !sizes failed for {image_key}: {e}")
        return {}


def fetch_download_url(image_key):
    try:
        d = smugmug_get(f"image/{image_key}!download")
        return d.get("Response", {}).get("ImageDownload", {}).get("Url", "")
    except Exception as e:
        print(f"    WARNING: !download failed for {image_key}: {e}")
        return ""


def fetch_album_videos(album_key):
    videos = []
    start, count = 1, 100
    while True:
        data  = smugmug_get(f"album/{album_key}!images",
                            {"count": str(count), "start": str(start)})
        resp  = data.get("Response", {})
        items = resp.get("AlbumImage", [])

        for item in items:
            fname = item.get("FileName", "")
            if not fname.lower().endswith((".mp4", ".mov", ".m4v")):
                continue
            web_uri   = item.get("WebUri", "")
            image_uri = item.get("Uris", {}).get("Image", {}).get("Uri", "")
            image_key = image_uri.split("/")[-1] if image_uri else ""
            if not image_key:
                continue

            print(f"  Fetching URLs for: {fname}")
            sizes    = fetch_sizes(image_key)
            thumb    = (sizes.get("X3LargeImageUrl") or sizes.get("LargeImageUrl")
                        or sizes.get("ThumbImageUrl") or "")
            vid_url  = (sizes.get("LargestVideoUrl") or sizes.get("1920VideoUrl")
                        or sizes.get("1280VideoUrl") or "")
            dl_url   = fetch_download_url(image_key) or vid_url

            stem = fname.rsplit(".", 1)[0]
            videos.append({
                "filename":      fname,
                "stem":          stem,
                "smugmug_url":   web_uri,
                "thumbnail_url": thumb,
                "download_url":  dl_url,
                "video_file_url": vid_url,
            })

        pages = resp.get("Pages", {})
        total = pages.get("Total", 0)
        if start + count - 1 >= total:
            break
        start += count

    return videos


# ── Master CSV loading ──────────────────────────────────────────────────────

def normalize(s):
    """Lowercase, strip accents, collapse whitespace."""
    s = str(s or "").strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).lower()


def load_master_csv(path, ceremony_filter, degree_filter):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_val   = row.get("Ceremoney Time", "").strip()
            degree_val = row.get("Degree Level", "").strip()
            if ceremony_filter and ceremony_filter.upper() not in time_val.upper():
                continue
            if degree_filter and degree_val != degree_filter:
                continue
            rows.append(row)
    return rows


# ── Matching logic ─────────────────────────────────────────────────────────

def make_keys(row):
    """
    Generate all match keys for a CSV row:
      (1) "lastname-full name" dash style
      (2) "lastname_firstname" underscore style
    """
    fn   = normalize(row.get("First Name", ""))
    ln   = normalize(row.get("Last Name", ""))
    full = normalize(row.get("Full Name (Combined)", ""))

    # Reconstruct raw values for exact-stem matching
    raw_fn   = str(row.get("First Name", "")).strip()
    raw_ln   = str(row.get("Last Name", "")).strip()
    raw_full = str(row.get("Full Name (Combined)", "")).strip()

    keys = set()

    # Strategy 1: exact "LastName-Full Name Combined" stem (e.g. "Cecil-Jared R. Cecil")
    keys.add(normalize(f"{raw_ln}-{raw_full}"))
    # with double-space collapsed
    keys.add(normalize(re.sub(r"\s+", " ", f"{raw_ln}-{raw_full}")))

    # Strategy 2: "LastName_FirstName" underscore stem (e.g. "Stewart_Shkera")
    keys.add(f"{ln}_{fn}")
    keys.add(f"{ln}_{fn.split()[0] if fn else ''}")   # only first word of first name

    # Strategy 3: just last_first with space
    keys.add(f"{ln} {fn}")

    return keys


def build_csv_index(csv_rows):
    """Build a dict: normalize(key) → csv_row for all strategies."""
    index = {}
    for row in csv_rows:
        for k in make_keys(row):
            k = k.strip()
            if k:
                index[k] = row
    return index


def stem_key(stem):
    """Normalize a SmugMug filename stem for lookup."""
    return normalize(re.sub(r"\s+", " ", stem))


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    print(f"\nUOPX 2026 — AM Associates Import Builder")
    print(f"{'─' * 50}\n")

    # ── Load master CSV ──
    print(f"Loading master CSV: {MASTER_CSV}")
    csv_rows = load_master_csv(MASTER_CSV, CEREMONY_FILTER, DEGREE_FILTER)
    print(f"  AM Associates rows: {len(csv_rows)}")

    # Build t → row index
    t_index = {str(r.get("t", "")).strip(): r for r in csv_rows}

    if "--csv-only" in args:
        for r in csv_rows:
            print(f"  {r.get('t',''):<12} {r.get('Full Name (Combined)', '')}")
        return

    # ── Fetch SmugMug videos ──
    print(f"\nFetching SmugMug album {ALBUM_KEY}...")
    sm_videos = fetch_album_videos(ALBUM_KEY)
    print(f"  Videos found: {len(sm_videos)}")

    if "--sm-only" in args:
        for v in sm_videos:
            print(f"  {v['stem']}")
        return

    # ── Build CSV index ──
    csv_index = build_csv_index(csv_rows)

    # ── Match ──
    print(f"\nMatching...\n")
    matched_rows = []
    sm_matched   = set()
    csv_matched  = set()

    for v in sm_videos:
        stem = v["stem"]
        t_val = None

        # 1. Manual override (normalize whitespace before lookup)
        stem_norm = re.sub(r"\s+", " ", stem).strip()
        if stem_norm in MANUAL_OVERRIDES:
            t_val = MANUAL_OVERRIDES[stem_norm]
            print(f"  MANUAL  {stem} → t={t_val}")

        # 2. Normalized stem lookup
        if t_val is None:
            key = stem_key(stem)
            csv_row = csv_index.get(key)
            if csv_row:
                t_val = str(csv_row.get("t", "")).strip()

        if t_val is None:
            print(f"  MISS    {stem}")
            continue

        csv_row = t_index.get(t_val)
        if not csv_row:
            print(f"  BAD-T   stem={stem} t={t_val} — not found in CSV")
            continue

        sm_matched.add(stem)
        csv_matched.add(t_val)

        student_id   = f"UOPX-AM-ASSOC-{t_val}"
        full_name    = csv_row.get("Full Name (Combined)", "").strip()
        first_name   = csv_row.get("First Name", "").strip()
        last_name    = csv_row.get("Last Name", "").strip()
        search_name  = full_name  # used by ilike search
        degree_title = csv_row.get("DegreeTitle", "").strip()

        matched_rows.append({
            "student_id":    student_id,
            "student_name":  full_name,
            "search_name":   search_name,
            "first_name":    first_name,
            "last_name":     last_name,
            "school_name":   SCHOOL_NAME,
            "event_name":    EVENT_NAME,
            "event_year":    EVENT_YEAR,
            "degree_name":   degree_title,
            "thumbnail_url": v["thumbnail_url"],
            "smugmug_url":   v["smugmug_url"],
            "download_url":  v["download_url"],
            "video_file_url": v["video_file_url"],
            "status":        "uploaded",
            "is_active":     "false",
        })

    # ── Summary ──
    print(f"\n{'─' * 50}")
    print(f"  Matched:       {len(matched_rows)}")
    print(f"  SM unmatched:  {len(sm_videos) - len(sm_matched)}")
    print(f"  CSV unmatched: {len(csv_rows) - len(csv_matched)}")
    print(f"{'─' * 50}")

    unmatched_sm = [v["stem"] for v in sm_videos if v["stem"] not in sm_matched]
    if unmatched_sm:
        print(f"\nSmugMug stems with NO CSV match:")
        for s in unmatched_sm:
            print(f"    {s}")

    unmatched_csv = [(r.get("t",""), r.get("Full Name (Combined)",""))
                     for r in csv_rows if str(r.get("t","")).strip() not in csv_matched]
    if unmatched_csv:
        print(f"\nCSV rows with NO video match:")
        for t, name in unmatched_csv:
            print(f"    {t:<12} {name}")

    # ── Write output ──
    if not matched_rows:
        print("\nNo rows matched — nothing written.")
        return

    fieldnames = [
        "student_id", "student_name", "search_name", "first_name", "last_name",
        "school_name", "event_name", "event_year", "degree_name",
        "thumbnail_url", "smugmug_url", "download_url", "video_file_url",
        "status", "is_active",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_rows)

    print(f"\nWritten: {OUTPUT_FILE}  ({len(matched_rows)} rows)")
    print(f"Next: import into Supabase public.videos table\n")


if __name__ == "__main__":
    main()
