#!/usr/bin/env python3
"""
UOPX 2026 — Multi-Group Supabase Importer
==========================================
Reads all groups from the Excel file, fetches SmugMug URLs, matches by
name, and upserts complete records into Supabase.

Usage:
  python3 uopx-multi-import.py                  # run all groups
  python3 uopx-multi-import.py "Bach AM"         # single group
  python3 uopx-multi-import.py "Bach AM" --dry-run
  python3 uopx-multi-import.py --list            # show groups + counts
"""

import sys, csv, json, hmac, hashlib, base64, time, random, string
import re, unicodedata, urllib.request, urllib.parse
import openpyxl
import smugmug_config as cfg
import secrets_local as _secrets  # gitignored; holds API keys

# ── Config ─────────────────────────────────────────────────────────────────
EXCEL_FILE   = "/Users/isaacgonzalez/Downloads/Round 2 Slide Verification 4.13-14.xlsx"
SUPABASE_URL = "https://uqfxjqkwicoljgztkijw.supabase.co"
SUPABASE_KEY = _secrets.SUPABASE_KEY
SMUGMUG_BASE = "https://www.smugmug.com/api/v2"
SCHOOL_NAME  = "University of Phoenix"
EVENT_YEAR   = 2026

GROUPS = {
    # sheet_name: (id_prefix, album_key, event_name)
    "AA AM":      ("UOPX-AM-ASSOC", "pC2pK8", "AM Ceremony"),
    "Bach AM":    ("UOPX-AM-BACH",  "8bRWHq", "AM Ceremony"),
    "Masters AM": ("UOPX-AM-MAST",  "LfZVFK", "AM Ceremony"),
    "Doc AM":     ("UOPX-AM-DOC",   "sZFf6Q", "AM Ceremony"),
    "AA PM":      ("UOPX-PM-ASSOC", "GrRVRF", "PM Ceremony"),
    "Bach PM":    ("UOPX-PM-BACH",  "jcFwsr", "PM Ceremony"),
    "Masters PM": ("UOPX-PM-MAST",  "h98srf", "PM Ceremony"),
    "Doc PM":     ("UOPX-PM-DOC",   "mk9DPL", "PM Ceremony"),
}

# Manual overrides: normalized stem → PERS number
# Used when auto name-matching fails (apostrophes, hyphens, typos, last-name-only files)
MANUAL_OVERRIDES = {
    "Bach AM": {
        "adebara":                                    "9026835759",  # Adejumoke Adebara
        "diaz_david_oscar":                           "9056193963",  # David Diaz (2nd)
        "eichelberger-t-cheri eichelberger":          "9036978157",  # Tanesha-Cheri Eichelberger
        "latoya johnston":                            "9027130254",  # LaToya Johnson Ferchaud
        "lesane-tyana sherell le'sane":               "9059663624",  # Tyana Le'Sane
        "maysmays-melissa k. maysmays":               "9056927275",  # Melissa Mays
        "mccalla-kimberly l. crenshaw-mccalla":       "9035314153",  # Kimberly Crenshaw-McCalla
        "mitchell-watson-teresa m. mitchell":         "9059316664",  # Teresa Mitchell
        "reed-redmond-markella reed-redmond":         "9010045912",  # Markella Reed-Redmond
        "sanders-william-sanders":                    "9054093108",  # William Sanders
    },
    "Masters AM": {
        "acevedo-alejandro acevedo":                  "9059460448",  # Alejandro Acevedo (first name missing in Excel)
        "arbelo_melissa":                             "9053866310",  # Melissa Arbelo-Rodriguez (hyphenated last)
        "bustos-marisa bustos-segoviano":             "9054228510",  # Marisa Bustos-Segoviano (hyphenated last)
        "moutari-moussa-maman lawan moutari-moussa":  "9037691707",  # Maman Lawan Moutari-Moussa (hyphenated last)
        "st.mary-joseph jerome st.mary, jr.":         "9059820754",  # Joseph St. Mary Jr. (no space in filename)
        "st.souver-christina st.souver":              "9059613390",  # Christina St. Souver (no space in filename)
    },
    "AA PM": {
        "anderson-culp-troi denay d. anderson-culp":  "9059852417",  # Troi Denay Anderson-Culp (hyphenated last)
        "davis_samaria":                              "9058179021",  # Samaria Davis-Hodges (hyphenated last)
        "gilges-1-30 pm michelle gilges":             "9010414044",  # Heather Gilges (⚠ video says Michelle, Excel says Heather)
        "paz rodriguez-mery judyth paz rodriguez":    "9059179020",  # Mery Paz (compound last name)
        "ramey-missy raenell ramey":                  "9058615964",  # Michelda Ramey (⚠ video says Missy, likely nickname)
        "stmary-onystie stmary":                      "9058388702",  # Onystie St. Mary (no space/period in filename)
        "hill-roycelyn vannell hill":                 "9059064103",  # Roycelyn Wytch (⚠ video lastname Hill ≠ Excel lastname Wytch)
    },
    "Bach PM": {
        "el-khoury hanna-christina a. el-khoury hanna": "9033579410",  # Christina El-Khoury Hanna (compound last)
        "joohnson_danielle":                          "9059154585",  # Danielle Johnson (typo double-o)
        "lopezgarcia-stephanie d. lopezgarcia":       "9058554710",  # Stephanie Lopez (filename uses LopezGarcia)
        "snell-rene marie snell":                     "9035552013",  # Rene' Snell (apostrophe in name breaks matching)
        "wright iii-latosha n. wright iii":           "9050655038",  # La'Tosha Wright III (apostrophe in name)
    },
    "Masters PM": {
        "chapman, sr-eric tremell chapman, sr.":      "3001073524",  # Eric Chapman Sr. (comma+suffix in last name)
        "mccorkle-roneesha la shaun mccorkle":        "9020661381",  # Roneesha Mc Corkle (space in Mc Corkle)
        "rivera_gilberto":                            "9059773945",  # Gilberto Vélez Rivera (compound last name)
    },
}

SB_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def normalize(s):
    s = str(s or "").strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).lower()

def clean_pers(val):
    s = str(val or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s if s and s not in ("None", "") else ""


# ── OAuth ───────────────────────────────────────────────────────────────────

def _pct(s): return urllib.parse.quote(str(s), safe="")

def oauth_header(method, base_url, qp):
    op = {
        "oauth_consumer_key":     cfg.SMUGMUG_API_KEY,
        "oauth_nonce":            "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_version":          "1.0",
        "oauth_token":            cfg.SMUGMUG_ACCESS_TOKEN,
    }
    all_p     = {**qp, **op}
    param_str = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(all_p.items()))
    base_str  = "&".join([method.upper(), _pct(base_url), _pct(param_str)])
    sk        = _pct(cfg.SMUGMUG_API_SECRET) + "&" + _pct(cfg.SMUGMUG_ACCESS_TOKEN_SECRET)
    sig       = base64.b64encode(
        hmac.new(sk.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    op["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{k}="{_pct(v)}"' for k, v in sorted(op.items()))

def smugmug_get(endpoint, params=None):
    base_url = f"{SMUGMUG_BASE}/{endpoint}"
    qp = {"_accept": "application/json"}
    if params: qp.update(params)
    req = urllib.request.Request(
        f"{base_url}?{urllib.parse.urlencode(qp)}",
        headers={"Accept": "application/json", "Authorization": oauth_header("GET", base_url, qp)},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def fetch_sizes(image_key):
    try:
        d = smugmug_get(f"image/{image_key}!sizes")
        return d.get("Response", {}).get("ImageSizes", {})
    except Exception as e:
        print(f"    WARNING: !sizes failed for {image_key}: {e}")
        return {}

def derive_download_url(vid_url):
    """Derive download URL from video URL — avoids a second API call per video."""
    if not vid_url:
        return ""
    # e.g. .../1920/i-ABC-1920.mp4  →  .../1920D/i-ABC-1920D.mp4
    return re.sub(r"/1920/(.+)-1920\.mp4$", r"/1920D/\1-1920D.mp4", vid_url)

def fetch_album_videos(album_key):
    videos, start, count = [], 1, 100
    while True:
        data  = smugmug_get(f"album/{album_key}!images", {"count": str(count), "start": str(start)})
        resp  = data.get("Response", {})
        items = resp.get("AlbumImage", [])
        for item in items:
            fname = item.get("FileName", "")
            if not fname.lower().endswith((".mp4", ".mov", ".m4v")):
                continue
            image_uri = item.get("Uris", {}).get("Image", {}).get("Uri", "")
            image_key = image_uri.split("/")[-1] if image_uri else ""
            if not image_key:
                continue
            sizes   = fetch_sizes(image_key)
            thumb   = sizes.get("X3LargeImageUrl") or sizes.get("LargeImageUrl") or sizes.get("ThumbImageUrl") or ""
            vid_url = sizes.get("LargestVideoUrl") or sizes.get("1920VideoUrl") or sizes.get("1280VideoUrl") or ""
            dl_url  = derive_download_url(vid_url) or vid_url
            videos.append({
                "filename":       fname,
                "stem":           fname.rsplit(".", 1)[0],
                "smugmug_url":    item.get("WebUri", ""),
                "thumbnail_url":  thumb,
                "download_url":   dl_url,
                "video_file_url": vid_url,
            })
        pages = resp.get("Pages", {})
        total = pages.get("Total", 0)
        if start + count - 1 >= total:
            break
        start += count
    return videos


# ── Excel loading ────────────────────────────────────────────────────────────

def load_sheet(sheet_name):
    """Return list of dicts with keys: pers, first, last, degree, middle."""
    wb   = openpyxl.load_workbook(EXCEL_FILE, read_only=True, data_only=True)
    ws   = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Find header row (contains PERS)
    header_idx = 0
    for i, row in enumerate(rows):
        if any(c and "PERS" in str(c).upper() for c in row):
            header_idx = i
            break

    header = [str(c).strip() if c else "" for c in rows[header_idx]]

    def col(name): return next((i for i, h in enumerate(header) if h.upper().startswith(name.upper())), None)

    pers_col   = col("PERS")
    first_col  = col("FIRST")
    last_col   = col("LAST")
    mid_col    = col("MIDDLE")
    degree_col = col("DEGREE")

    students = []
    for row in rows[header_idx + 1:]:
        if not row: continue
        def cell(col): return row[col] if col is not None and len(row) > col else None
        pers = clean_pers(cell(pers_col))
        if not pers: continue
        first  = str(cell(first_col) or "").strip()
        last   = str(cell(last_col)  or "").strip()
        middle = str(cell(mid_col)   or "").strip()
        degree = str(cell(degree_col)or "").strip()
        # Strip "Dr." prefix from first name (Doctoral sheets)
        first_clean = re.sub(r"^Dr\.\s*", "", first, flags=re.IGNORECASE).strip()
        students.append({
            "pers":   pers,
            "first":  first_clean,
            "last":   last,
            "middle": middle,
            "degree": degree,
        })
    return students


# ── Name matching ────────────────────────────────────────────────────────────

def build_name_index(students):
    """
    Build lookup: normalized_key → student
    Keys generated per student:
      - normalize(last) + "-" + normalize(first)           → "acclise-angel"
      - normalize(last) + "_" + normalize(first)           → "acclise_angel"
      - normalize(last) + "_" + normalize(first_word)      → for middle-name variants
      - normalize(last) + " " + normalize(first)           → plain
    """
    index = {}
    for s in students:
        nl = normalize(s["last"])
        nf = normalize(s["first"])
        fw = nf.split()[0] if nf else nf   # first word only
        for key in {
            f"{nl}-{nf}", f"{nl}_{nf}", f"{nl}_{fw}", f"{nl} {nf}", f"{nl} {fw}",
        }:
            if key.strip():
                index[key] = s
    return index

def parse_stem(stem):
    """
    Parse a SmugMug filename stem into (last, first) for lookup.

    Handles:
      LastName-FirstName [Middle] LastName   → most albums
      LastName_FirstName                     → some AA PM
      AM LastName_FirstName                  → some Bach AM (strip AM/PM prefix)
      LastName                               → incomplete, returns (last, "")
    """
    # Strip leading "AM " or "PM " prefix
    stem = re.sub(r"^(AM|PM)\s+", "", stem, flags=re.IGNORECASE).strip()

    if "-" in stem:
        parts = stem.split("-", 1)
        last  = normalize(parts[0])
        rest  = parts[1].strip() if len(parts) > 1 else ""
        # Strip "Dr." prefix (Doctoral albums use "LastName-Dr. FirstName LastName")
        rest  = re.sub(r"^Dr\.\s*", "", rest, flags=re.IGNORECASE).strip()
        # rest is like "Angel Lorian Acclise" — first word is first name
        first = normalize(rest.split()[0]) if rest else ""
        return last, first
    elif "_" in stem:
        parts = stem.split("_", 1)
        last  = normalize(parts[0])
        first = normalize(parts[1].split()[0]) if len(parts) > 1 else ""
        return last, first
    else:
        return normalize(stem), ""

def match_video(stem, index):
    """Return student dict or None."""
    last, first = parse_stem(stem)
    if not last:
        return None
    for key in [
        f"{last}-{first}", f"{last}_{first}", f"{last} {first}",
        f"{last}-",        f"{last}_",        f"{last} ",
    ]:
        if key.rstrip("-_ ") == last:  # last-only fallback — skip ambiguous
            continue
        result = index.get(key)
        if result:
            return result
    # Last-only fallback only if unambiguous (single student with that last name)
    matching = [v for k, v in index.items() if k.split("-")[0].split("_")[0].split(" ")[0] == last]
    if len(matching) == 1:
        return matching[0]
    return None


# ── Supabase upsert ──────────────────────────────────────────────────────────

def upsert_batch(rows, dry_run=False):
    if dry_run:
        for r in rows[:3]:
            print(f"    DRY: {r['student_id']} | {r['student_name']}")
        if len(rows) > 3:
            print(f"    ... and {len(rows)-3} more")
        return len(rows), 0

    ok = errors = 0
    BATCH = 50
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i+BATCH]
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/videos?on_conflict=student_id",
            data=json.dumps(chunk).encode(),
            headers={**SB_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as r:
                ok += len(json.loads(r.read()) or [])
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"    BATCH ERROR {e.code}: {body[:200]}")
            errors += len(chunk)
    return ok, errors


# ── Group runner ─────────────────────────────────────────────────────────────

def run_group(sheet_name, dry_run=False):
    prefix, album_key, event_name = GROUPS[sheet_name]
    overrides = MANUAL_OVERRIDES.get(sheet_name, {})

    print(f"\n{'═'*60}")
    print(f"  {sheet_name}  |  album: {album_key}  |  prefix: {prefix}")
    print(f"{'═'*60}")

    # Load Excel students
    students = load_sheet(sheet_name)
    print(f"  Excel rows:  {len(students)}")
    index    = build_name_index(students)
    pers_map = {s["pers"]: s for s in students}

    # Fetch SmugMug
    print(f"  Fetching SmugMug album {album_key}...")
    videos = fetch_album_videos(album_key)
    print(f"  Videos:      {len(videos)}")

    # Match
    rows        = []
    matched_ids = set()
    unmatched   = []

    for v in videos:
        # Check manual override first
        stem_norm = normalize(v["stem"])
        pers_override = overrides.get(stem_norm)
        if pers_override:
            student = pers_map.get(pers_override)
            if student:
                print(f"  OVERRIDE {v['stem']} → {pers_override}")
            else:
                print(f"  BAD OVERRIDE {v['stem']} → {pers_override} not in Excel")
                student = None
        else:
            student = match_video(v["stem"], index)

        if not student:
            unmatched.append(v["stem"])
            continue

        pers = student["pers"]
        if pers in matched_ids:
            print(f"  DUPE: {pers} matched by multiple videos (stem={v['stem']})")
            continue
        matched_ids.add(pers)

        first  = student["first"]
        middle = student["middle"]
        last   = student["last"]
        name_parts = [p for p in [first, middle, last] if p]
        full_name  = " ".join(name_parts)

        rows.append({
            "student_id":     f"{prefix}-{pers}",
            "student_name":   full_name,
            "first_name":     first,
            "last_name":      last,
            "school_name":    SCHOOL_NAME,
            "event_name":     event_name,
            "event_year":     EVENT_YEAR,
            "degree_name":    student["degree"],
            "thumbnail_url":  v["thumbnail_url"],
            "smugmug_url":    v["smugmug_url"],
            "download_url":   v["download_url"],
            "video_file_url": v["video_file_url"],
            "status":         "uploaded",
            "is_active":      False,
        })

    # Report
    print(f"\n  Matched:     {len(rows)}")
    print(f"  Unmatched:   {len(unmatched)}")
    if unmatched:
        print(f"\n  Unmatched SmugMug stems:")
        for s in unmatched:
            print(f"    {s}")

    unmatched_students = [s for s in students if s["pers"] not in matched_ids]
    if unmatched_students:
        print(f"\n  Students with no video ({len(unmatched_students)}):")
        for s in unmatched_students[:20]:
            print(f"    {s['pers']}  {s['first']} {s['last']}")
        if len(unmatched_students) > 20:
            print(f"    ... and {len(unmatched_students)-20} more")

    # Upsert
    if rows:
        print(f"\n  Upserting {len(rows)} rows to Supabase...")
        ok, errors = upsert_batch(rows, dry_run)
        print(f"  OK: {ok}   Errors: {errors}")
    else:
        print(f"\n  Nothing to upsert.")

    return len(rows), len(unmatched)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args     = sys.argv[1:]
    dry_run  = "--dry-run" in args
    list_grp = "--list" in args
    targets  = [a for a in args if not a.startswith("--")]

    if list_grp:
        print("\nAvailable groups:")
        for g, (prefix, album_key, event_name) in GROUPS.items():
            print(f"  {g:<14}  prefix={prefix:<16}  album={album_key}")
        return

    run_groups = targets if targets else list(GROUPS.keys())

    # Skip AA AM — already imported
    if not targets and "AA AM" in run_groups:
        run_groups.remove("AA AM")
        print("Skipping AA AM (already imported).")

    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"\nUOPX 2026 — Multi-Group Importer  [{mode}]")
    print(f"Groups to process: {run_groups}\n")

    total_matched = total_unmatched = 0
    for group in run_groups:
        if group not in GROUPS:
            print(f"Unknown group: {group}. Use --list to see options.")
            continue
        m, u = run_group(group, dry_run)
        total_matched   += m
        total_unmatched += u

    print(f"\n{'═'*60}")
    print(f"  DONE — Matched: {total_matched}   Unmatched: {total_unmatched}")
    print(f"  Records are is_active=false — set to true when ready to go live.")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
