#!/usr/bin/env python3
"""
One-off fix: find new Lagneaux video in SmugMug and update Supabase record.
"""
import json, hmac, hashlib, base64, time, random, string
import urllib.request, urllib.parse

import smugmug_config as cfg
import secrets_local as _secrets  # gitignored; holds API keys

SMUGMUG_BASE = "https://www.smugmug.com/api/v2"
SUPABASE_URL = "https://uqfxjqkwicoljgztkijw.supabase.co"
SUPABASE_KEY = _secrets.SUPABASE_KEY

STUDENT_ID  = "UOPX-PM-BACH-9059309377"
TARGET_FILE = "Lagneaux - Natalie Meche Lagneaux.mp4"
# PM Bach album key
ALBUM_KEY   = "jcFwsr"


def oauth_header(method, base_url, query_params):
    pct = lambda s: urllib.parse.quote(str(s), safe='')
    op = {
        "oauth_consumer_key":     cfg.SMUGMUG_API_KEY,
        "oauth_nonce":            ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_version":          "1.0",
        "oauth_token":            cfg.SMUGMUG_ACCESS_TOKEN,
    }
    all_p    = {**query_params, **op}
    param_str = "&".join(f"{pct(k)}={pct(v)}" for k, v in sorted(all_p.items()))
    base_str  = "&".join([method.upper(), pct(base_url), pct(param_str)])
    sign_key  = pct(cfg.SMUGMUG_API_SECRET) + "&" + pct(cfg.SMUGMUG_ACCESS_TOKEN_SECRET)
    sig = base64.b64encode(
        hmac.new(sign_key.encode(), base_str.encode(), hashlib.sha1).digest()
    ).decode()
    op["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{k}="{pct(v)}"' for k, v in sorted(op.items()))


def smug_get(endpoint, params=None):
    base_url = f"{SMUGMUG_BASE}/{endpoint}"
    qp = {"_accept": "application/json"}
    if params:
        qp.update(params)
    headers = {"Accept": "application/json", "Authorization": oauth_header("GET", base_url, qp)}
    url = f"{base_url}?{urllib.parse.urlencode(qp)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
        return json.loads(r.read())


def find_video_in_album(album_key, target_filename):
    start = 1
    while True:
        data  = smug_get(f"album/{album_key}!images", {"count": "100", "start": str(start)})
        resp  = data.get("Response", {})
        items = resp.get("AlbumImage", [])
        for item in items:
            if item.get("FileName", "").lower() == target_filename.lower():
                return item
        pages = resp.get("Pages", {})
        if start + 100 - 1 >= pages.get("Total", 0):
            break
        start += 100
    return None


def get_image_key(item):
    uri = item.get("Uris", {}).get("Image", {}).get("Uri", "")
    return uri.split("/")[-1] if uri else ""


def fetch_sizes(image_key):
    try:
        return smug_get(f"image/{image_key}!sizes").get("Response", {}).get("ImageSizes", {})
    except Exception as e:
        print(f"  WARNING sizes: {e}")
        return {}


def fetch_download(image_key):
    try:
        return smug_get(f"image/{image_key}!download").get("Response", {}).get("ImageDownload", {}).get("Url", "")
    except Exception as e:
        print(f"  WARNING download: {e}")
        return ""


def patch_supabase(student_id, payload):
    params = urllib.parse.urlencode({"student_id": f"eq.{student_id}"})
    url    = f"{SUPABASE_URL}/rest/v1/videos?{params}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="PATCH")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main():
    print(f"Searching PM Bach album ({ALBUM_KEY}) for: {TARGET_FILE}\n")

    item = find_video_in_album(ALBUM_KEY, TARGET_FILE)
    if not item:
        print(f"NOT FOUND — '{TARGET_FILE}' not in album {ALBUM_KEY}.")
        print("Check that the new video was uploaded to the correct SmugMug album.")
        return

    image_key = get_image_key(item)
    web_uri   = item.get("WebUri", "")
    print(f"Found! ImageKey={image_key}  WebUri={web_uri}")

    sizes         = fetch_sizes(image_key)
    thumbnail_url = sizes.get("X3LargeImageUrl") or sizes.get("LargeImageUrl") or sizes.get("ThumbImageUrl") or ""
    video_file_url = sizes.get("LargestVideoUrl") or sizes.get("1920VideoUrl") or sizes.get("1280VideoUrl") or ""
    download_url  = fetch_download(image_key) or video_file_url

    print(f"\nNew URLs:")
    print(f"  thumbnail_url:  {thumbnail_url}")
    print(f"  smugmug_url:    {web_uri}")
    print(f"  download_url:   {download_url}")
    print(f"  video_file_url: {video_file_url}")

    payload = {
        "thumbnail_url":   thumbnail_url,
        "smugmug_url":     web_uri,
        "download_url":    download_url,
        "video_file_url":  video_file_url,
        "status":          "uploaded",
    }

    print(f"\nPatching Supabase record {STUDENT_ID}...")
    result = patch_supabase(STUDENT_ID, payload)
    if result:
        print(f"OK — record updated for {result[0].get('student_name', STUDENT_ID)}")
    else:
        print("Patch returned empty result — check Supabase for STUDENT_ID.")


if __name__ == "__main__":
    main()
