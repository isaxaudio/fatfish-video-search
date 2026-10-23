#!/usr/bin/env python3
"""
FF Video Platform — SmugMug URL Exporter
==========================================
Reads all videos from a SmugMug album, matches each to a Supabase
student_id by parsing the filename, and outputs a CSV ready for
bulk-update.py.

Usage:
  python3 smugmug-export.py <album-key>
  python3 smugmug-export.py <album-key> --dry-run

Example:
  python3 smugmug-export.py wZXWTJ
  python3 smugmug-export.py wZXWTJ --dry-run

To find your album key, run:
  python3 smugmug-export.py --list-albums

Filename convention expected:
  LastName_FirstName_DegreeAbbrev_City_Year.mp4
  e.g. Rodriguez_Maria_MBA_Dallas_2025.mp4

Output CSV columns:
  student_id, thumbnail_url, smugmug_url, download_url, video_file_url, status
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
import secrets_local as _secrets  # gitignored; holds API keys

# ── CONFIG ────────────────────────────────────────────────────────────────────
SMUGMUG_API_KEY = _secrets.SMUGMUG_API_KEY
SMUGMUG_USERNAME = "fatfish"
SMUGMUG_BASE     = "https://www.smugmug.com/api/v2"

SUPABASE_URL = "https://uqfxjqkwicoljgztkijw.supabase.co"
SUPABASE_KEY = _secrets.SUPABASE_KEY

OUTPUT_FILE = "urls-ready.csv"
# ─────────────────────────────────────────────────────────────────────────────

# ── OAuth (loaded from smugmug_config.py if available) ───────────────────────
_OAUTH = None
try:
    import smugmug_config as _cfg
    _OAUTH = {
        "key":          _cfg.SMUGMUG_API_KEY,
        "secret":       _cfg.SMUGMUG_API_SECRET,
        "token":        _cfg.SMUGMUG_ACCESS_TOKEN,
        "token_secret": _cfg.SMUGMUG_ACCESS_TOKEN_SECRET,
    }
    SMUGMUG_API_KEY  = _cfg.SMUGMUG_API_KEY
    SMUGMUG_USERNAME = _cfg.SMUGMUG_USERNAME
    print("Auth: OAuth (smugmug_config.py)")
except ImportError:
    print("Auth: API key only (smugmug_config.py not found — LargestVideo may be unavailable)")


def _oauth_header(method, base_url, query_params):
    """Build OAuth 1.0a Authorization header. Signature covers query + oauth params."""
    pct = lambda s: urllib.parse.quote(str(s), safe='')

    oauth_p = {
        "oauth_consumer_key":     _OAUTH["key"],
        "oauth_nonce":            ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_version":          "1.0",
        "oauth_token":            _OAUTH["token"],
    }

    # Signature base string covers ALL params (query params + oauth params)
    all_params = {**query_params, **oauth_p}
    param_str  = "&".join(f"{pct(k)}={pct(v)}" for k, v in sorted(all_params.items()))
    base_str   = "&".join([method.upper(), pct(base_url), pct(param_str)])
    signing_key = pct(_OAUTH["secret"]) + "&" + pct(_OAUTH["token_secret"])

    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_p["oauth_signature"] = sig

    return "OAuth " + ", ".join(
        f'{k}="{pct(v)}"' for k, v in sorted(oauth_p.items())
    )
# ─────────────────────────────────────────────────────────────────────────────


def smugmug_get(endpoint, params=None):
    """GET from SmugMug API. Uses OAuth if available, API key otherwise."""
    base_url     = f"{SMUGMUG_BASE}/{endpoint}"
    query_params = {"_accept": "application/json"}
    if params:
        query_params.update(params)

    if _OAUTH:
        headers = {
            "Accept":        "application/json",
            "Authorization": _oauth_header("GET", base_url, query_params),
        }
    else:
        query_params["APIKey"] = SMUGMUG_API_KEY
        headers = {"Accept": "application/json"}

    qs  = urllib.parse.urlencode(query_params)
    url = f"{base_url}?{qs}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def supabase_get(path, params):
    qs  = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/{path}?{qs}"
    req = urllib.request.Request(url, headers={
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def list_albums():
    print(f"\nFetching albums for {SMUGMUG_USERNAME}...\n")
    data   = smugmug_get(f"user/{SMUGMUG_USERNAME}!albums", {"count": "100"})
    albums = data.get("Response", {}).get("Album", [])
    print(f"{'Key':<12} {'Name'}")
    print("─" * 50)
    for a in albums:
        print(f"{a['AlbumKey']:<12} {a['Name']}")
    print()


def get_image_key(item):
    """Extract imageKey (e.g. 'wFn8t5R-0') from an AlbumImage Uris.Image.Uri."""
    uri = item.get("Uris", {}).get("Image", {}).get("Uri", "")
    return uri.split("/")[-1] if uri else ""


def fetch_image_sizes(image_key):
    """
    Call image/{key}!sizes directly.
    Returns the ImageSizes dict with X3LargeImageUrl, LargestVideoUrl, etc.
    _expand does NOT embed response data — this direct call is required.
    """
    try:
        data = smugmug_get(f"image/{image_key}!sizes")
        return data.get("Response", {}).get("ImageSizes", {})
    except Exception as e:
        print(f"    WARNING: !sizes call failed for {image_key}: {e}")
        return {}


def fetch_download_url(image_key):
    """
    Call image/{key}!download directly.
    Returns the download-intent URL (1920D.mp4) for the Download button.
    """
    try:
        data = smugmug_get(f"image/{image_key}!download")
        return data.get("Response", {}).get("ImageDownload", {}).get("Url", "")
    except Exception as e:
        print(f"    WARNING: !download call failed for {image_key}: {e}")
        return ""


def get_album_videos(album_key):
    """Return all video items from an album with correct direct asset URLs."""
    videos = []
    start  = 1
    count  = 100

    while True:
        # No _expand — it returns stubs only, not actual response data.
        # Real URLs are fetched via per-video direct API calls below.
        data = smugmug_get(
            f"album/{album_key}!images",
            {"count": str(count), "start": str(start)}
        )
        resp  = data.get("Response", {})
        items = resp.get("AlbumImage", [])

        for item in items:
            filename = item.get("FileName", "")
            if not filename.lower().endswith((".mp4", ".mov", ".m4v")):
                continue

            web_uri   = item.get("WebUri", "")
            image_key = get_image_key(item)

            if not image_key:
                print(f"    WARNING: no ImageKey found for {filename} — skipping")
                continue

            # ── Fetch sizes (thumbnail + video_file_url) ──
            sizes         = fetch_image_sizes(image_key)
            thumbnail_url = (
                sizes.get("X3LargeImageUrl")
                or sizes.get("LargeImageUrl")
                or sizes.get("ThumbImageUrl")
                or ""
            )
            video_file_url = (
                sizes.get("LargestVideoUrl")
                or sizes.get("1920VideoUrl")
                or sizes.get("1280VideoUrl")
                or ""
            )

            # ── Fetch download URL ──
            download_url = fetch_download_url(image_key)

            # Fallback: if download endpoint returned nothing, use video_file_url
            if not download_url:
                download_url = video_file_url

            videos.append({
                "filename":        filename,
                "smugmug_url":     web_uri,
                "thumbnail_url":   thumbnail_url,
                "download_url":    download_url,
                "video_file_url":  video_file_url,
                "_video_from_sizes": bool(sizes.get("LargestVideoUrl")),
            })

        pages = resp.get("Pages", {})
        total = pages.get("Total", 0)
        if start + count - 1 >= total:
            break
        start += count

    return videos


def parse_filename(filename):
    """
    Parse LastName_FirstName_Degree_City_Year.mp4
    Returns (first_name, last_name, event_year) or None if unparseable.
    """
    stem  = filename.rsplit(".", 1)[0]
    parts = stem.split("_")
    if len(parts) < 5:
        return None
    last_name  = parts[0].strip()
    first_name = parts[1].strip()
    try:
        event_year = int(parts[4].strip())
    except (ValueError, IndexError):
        event_year = None
    return first_name, last_name, event_year


def lookup_student_id(first_name, last_name, event_year):
    """Look up student_id in Supabase by name and year."""
    params = {
        "first_name": f"eq.{first_name}",
        "last_name":  f"eq.{last_name}",
        "select":     "student_id,student_name,event_name,event_year",
    }
    if event_year:
        params["event_year"] = f"eq.{event_year}"
    try:
        rows = supabase_get("videos", params)
        if rows:
            return rows[0]
    except Exception as e:
        print(f"    Supabase error for {first_name} {last_name}: {e}")
    return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--list-albums":
        list_albums()
        sys.exit(0)

    album_key = sys.argv[1]
    dry_run   = "--dry-run" in sys.argv

    print(f"\nFF Video Platform — SmugMug URL Exporter")
    print(f"Album key: {album_key}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXPORT'}\n")

    print("Fetching videos from SmugMug...")
    videos = get_album_videos(album_key)
    print(f"Found {len(videos)} video(s)\n")

    # Warn if any video had no LargestVideoUrl in !sizes
    fallback_count = sum(1 for v in videos if not v["_video_from_sizes"])
    if fallback_count:
        print(f"  WARNING: {fallback_count} video(s) had no LargestVideoUrl — "
              f"lower-resolution fallback used for video_file_url.\n")

    rows      = []
    matched   = 0
    unmatched = 0

    for v in videos:
        filename = v["filename"]
        parsed   = parse_filename(filename)

        if not parsed:
            print(f"  SKIP — can't parse filename: {filename}")
            unmatched += 1
            continue

        first_name, last_name, event_year = parsed
        record = lookup_student_id(first_name, last_name, event_year)

        if not record:
            print(f"  NOT FOUND — {first_name} {last_name} ({event_year}) not in Supabase")
            unmatched += 1
            continue

        student_id   = record.get("student_id", "")
        student_name = record.get("student_name", f"{first_name} {last_name}")

        if not student_id:
            print(f"  NO ID — {student_name} found in Supabase but has no student_id")
            unmatched += 1
            continue

        video_source = "LargestVideoUrl" if v["_video_from_sizes"] else "fallback resolution"

        row = {
            "student_id":    student_id,
            "thumbnail_url": v["thumbnail_url"],
            "smugmug_url":   v["smugmug_url"],
            "download_url":  v["download_url"],
            "video_file_url": v["video_file_url"],
            "status":        "uploaded",
        }
        rows.append(row)
        matched += 1

        print(f"  OK — {student_id} | {student_name}")
        if dry_run:
            print(f"    thumbnail_url:  {v['thumbnail_url']}")
            print(f"    smugmug_url:    {v['smugmug_url']}")
            print(f"    download_url:   {v['download_url']}")
            print(f"    video_file_url: {v['video_file_url']}  [{video_source}]")

    print(f"\n{'─' * 50}")
    print(f"  Matched:   {matched}")
    print(f"  Skipped:   {unmatched}")
    print(f"{'─' * 50}\n")

    if not rows:
        print("No rows to write. Check album key and filename convention.")
        sys.exit(1)

    if dry_run:
        print("Dry run — no file written.\n")
        sys.exit(0)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "student_id", "thumbnail_url", "smugmug_url",
            "download_url", "video_file_url", "status",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written: {OUTPUT_FILE}")
    print(f"Next:    python3 bulk-update.py {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()
