#!/usr/bin/env python3
"""
SmugMug OAuth 1.0a — One-Time Authorization
=============================================
Run this once to get your access token and access token secret.
Those two values go into smugmug-config.py and are reused forever.

Usage:
  python3 smugmug-auth.py

You will need:
  - API Key    (already in smugmug-export.py)
  - API Secret (from account.smugmug.com → API Keys)
"""

import sys
import hmac
import hashlib
import base64
import time
import urllib.request
import urllib.parse
import webbrowser
import os
import random
import string

# ── Your API Key (read-only half — already known) ────────────────────────────
API_KEY = "3J3vBwjVz7BbDzrRTXHhzwwcb7WkZmPM"

# ── SmugMug OAuth endpoints ───────────────────────────────────────────────────
REQUEST_TOKEN_URL = "https://www.smugmug.com/services/oauth/1.0a/getRequestToken"
AUTHORIZE_URL     = "https://www.smugmug.com/services/oauth/1.0a/authorize"
ACCESS_TOKEN_URL  = "https://www.smugmug.com/services/oauth/1.0a/getAccessToken"


# ── OAuth 1.0a helpers (stdlib only — no external packages needed) ────────────

def nonce():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def timestamp():
    return str(int(time.time()))


def percent_encode(s):
    return urllib.parse.quote(str(s), safe='')


def build_base_string(method, url, params):
    """RFC 5849 §3.4.1 — signature base string."""
    sorted_params = sorted(params.items())
    param_string  = "&".join(
        f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_params
    )
    return "&".join([
        method.upper(),
        percent_encode(url),
        percent_encode(param_string),
    ])


def build_signing_key(consumer_secret, token_secret=""):
    return percent_encode(consumer_secret) + "&" + percent_encode(token_secret)


def sign(base_string, signing_key):
    hashed = hmac.new(
        signing_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha1,
    )
    return base64.b64encode(hashed.digest()).decode()


def oauth_header(params):
    """Build Authorization: OAuth header string."""
    parts = ", ".join(
        f'{k}="{percent_encode(v)}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    )
    return f"OAuth {parts}"


def make_oauth_params(consumer_key, token=""):
    p = {
        "oauth_consumer_key":     consumer_key,
        "oauth_nonce":            nonce(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        timestamp(),
        "oauth_version":          "1.0",
    }
    if token:
        p["oauth_token"] = token
    return p


def post_oauth(url, consumer_key, consumer_secret,
               token="", token_secret="", extra_params=None):
    params = make_oauth_params(consumer_key, token)
    if extra_params:
        params.update(extra_params)

    base   = build_base_string("POST", url, params)
    key    = build_signing_key(consumer_secret, token_secret)
    params["oauth_signature"] = sign(base, key)

    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "Authorization": oauth_header(params),
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return dict(urllib.parse.parse_qsl(r.read().decode()))


# ── Main flow ─────────────────────────────────────────────────────────────────

def main():
    print("\nSmugMug OAuth — One-Time Authorization")
    print("=" * 42)

    api_secret = input("\nPaste your API Secret: ").strip()
    if not api_secret:
        print("ERROR: API secret is required.")
        sys.exit(1)

    # Step 1 — get a request token
    print("\nStep 1 — Requesting temporary token from SmugMug...")
    try:
        rt = post_oauth(
            REQUEST_TOKEN_URL,
            API_KEY,
            api_secret,
            extra_params={"oauth_callback": "oob"},
        )
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    request_token        = rt.get("oauth_token", "")
    request_token_secret = rt.get("oauth_token_secret", "")

    if not request_token:
        print("ERROR: No token returned. Check your API secret.")
        sys.exit(1)

    print("  Got temporary token.")

    # Step 2 — send user to authorize
    auth_url = (
        f"{AUTHORIZE_URL}"
        f"?oauth_token={request_token}"
        f"&Access=Full"
        f"&Permissions=Modify"
    )
    print(f"\nStep 2 — Opening SmugMug authorization page in your browser...")
    print(f"  URL: {auth_url}\n")
    print("  If the browser doesn't open automatically, copy the URL above.")
    webbrowser.open(auth_url)

    verifier = input("\nAfter you approve, SmugMug shows a 6-digit PIN. Enter it here: ").strip()
    if not verifier:
        print("ERROR: Verifier (PIN) is required.")
        sys.exit(1)

    # Step 3 — exchange for access token
    print("\nStep 3 — Exchanging for permanent access token...")
    try:
        at = post_oauth(
            ACCESS_TOKEN_URL,
            API_KEY,
            api_secret,
            token=request_token,
            token_secret=request_token_secret,
            extra_params={"oauth_verifier": verifier},
        )
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    access_token        = at.get("oauth_token", "")
    access_token_secret = at.get("oauth_token_secret", "")

    if not access_token:
        print("ERROR: No access token returned. Check the PIN and try again.")
        sys.exit(1)

    # Step 4 — write smugmug-config.py
    config_path = os.path.join(os.path.dirname(__file__), "smugmug_config.py")
    config_content = f'''# SmugMug OAuth credentials — generated by smugmug-auth.py
# Keep this file private. Do not commit to git.
SMUGMUG_API_KEY          = "{API_KEY}"
SMUGMUG_API_SECRET       = "{api_secret}"
SMUGMUG_ACCESS_TOKEN     = "{access_token}"
SMUGMUG_ACCESS_TOKEN_SECRET = "{access_token_secret}"
SMUGMUG_USERNAME         = "fatfish"
'''
    with open(config_path, "w") as f:
        f.write(config_content)

    print("\n" + "=" * 42)
    print("SUCCESS — OAuth authorized.")
    print(f"\nCredentials saved to: smugmug-config.py")
    print("\nThese values are permanent until you revoke access in SmugMug.")
    print("\nNext: run smugmug-folders.py to create your album structure.")


if __name__ == "__main__":
    main()
