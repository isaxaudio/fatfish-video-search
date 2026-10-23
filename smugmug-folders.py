#!/usr/bin/env python3
"""
SmugMug Folder + Album Creator
================================
Creates folders (node type "Folder") and galleries (node type "Album")
using OAuth 1.0a write access.

Requires smugmug-config.py — run smugmug-auth.py first if you haven't.

Usage:
  python3 smugmug-folders.py                  # create from STRUCTURE below
  python3 smugmug-folders.py --list           # list existing top-level folders
  python3 smugmug-folders.py --list <node-id> # list children of a node
"""

import sys
import hmac
import hashlib
import base64
import time
import json
import random
import string
import urllib.request
import urllib.parse

# ── Load credentials ──────────────────────────────────────────────────────────
try:
    from smugmug_config import (
        SMUGMUG_API_KEY,
        SMUGMUG_API_SECRET,
        SMUGMUG_ACCESS_TOKEN,
        SMUGMUG_ACCESS_TOKEN_SECRET,
        SMUGMUG_USERNAME,
    )
except ImportError:
    print("ERROR: smugmug-config.py not found.")
    print("       Run python3 smugmug-auth.py first.")
    sys.exit(1)

SMUGMUG_BASE = "https://www.smugmug.com/api/v2"

# ── Structure to create ───────────────────────────────────────────────────────
# Edit this to define what gets created.
# Each entry: (parent_node_id_or_None, type, name, privacy)
# None for parent = root level.
# Types: "Folder" or "Album"
# Privacy: "Public", "Unlisted", "Private"
STRUCTURE = [
    # (parent, type, name, privacy)
    (None,     "Folder", "UOPX 2026 Commencement", "Unlisted"),
    # Children are resolved automatically after parent is created
    ("UOPX 2026 Commencement", "Album", "AM Ceremony", "Unlisted"),
    ("UOPX 2026 Commencement", "Album", "PM Ceremony", "Unlisted"),
]

# ── OAuth helpers (stdlib only) ───────────────────────────────────────────────

def nonce():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def ts():
    return str(int(time.time()))

def pct(s):
    return urllib.parse.quote(str(s), safe='')

def base_string(method, url, params):
    sp = sorted(params.items())
    ps = "&".join(f"{pct(k)}={pct(v)}" for k, v in sp)
    return "&".join([method.upper(), pct(url), pct(ps)])

def signing_key(consumer_secret, token_secret=""):
    return pct(consumer_secret) + "&" + pct(token_secret)

def sign(bs, sk):
    h = hmac.new(sk.encode(), bs.encode(), hashlib.sha1)
    return base64.b64encode(h.digest()).decode()

def auth_header(params):
    parts = ", ".join(
        f'{k}="{pct(v)}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    )
    return f"OAuth {parts}"

def oauth_params(token=""):
    p = {
        "oauth_consumer_key":     SMUGMUG_API_KEY,
        "oauth_nonce":            nonce(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        ts(),
        "oauth_version":          "1.0",
    }
    if token:
        p["oauth_token"] = token
    return p


def signed_request(method, url, body=None, extra_oauth=None):
    """Make a signed OAuth request. body should be a dict or None."""
    # Split URL into base + query params (both must be in signature)
    parsed   = urllib.parse.urlparse(url)
    base_url = urllib.parse.urlunparse(parsed._replace(query=""))
    qs_params = dict(urllib.parse.parse_qsl(parsed.query))

    params = oauth_params(SMUGMUG_ACCESS_TOKEN)
    if extra_oauth:
        params.update(extra_oauth)

    # Merge URL query params into signature params
    sign_params = {**params, **qs_params}

    bs = base_string(method, base_url, sign_params)
    sk = signing_key(SMUGMUG_API_SECRET, SMUGMUG_ACCESS_TOKEN_SECRET)
    params["oauth_signature"] = sign(bs, sk)

    headers = {
        "Authorization": auth_header(params),
        "Accept":        "application/json",
    }

    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode()
        except Exception:
            err_body = "(no body)"
        return None, f"HTTP {e.code}: {err_body}"


# ── SmugMug API calls ─────────────────────────────────────────────────────────

def get_root_node():
    url = f"{SMUGMUG_BASE}/user/{SMUGMUG_USERNAME}"
    resp, err = signed_request("GET", url)
    if err:
        return None, err
    node_uri = resp["Response"]["User"]["Uris"]["Node"]["Uri"]
    node_id  = node_uri.split("/")[-1]
    return node_id, None


def list_children(node_id):
    url = f"{SMUGMUG_BASE}/node/{node_id}!children?count=100"
    resp, err = signed_request("GET", url)
    if err:
        return None, err
    nodes = resp.get("Response", {}).get("Node", [])
    return nodes, None


def create_node(parent_node_id, node_type, name, privacy="Unlisted"):
    url = f"{SMUGMUG_BASE}/node/{parent_node_id}!children"
    body = {
        "Type":              node_type,
        "Name":              name,
        "Privacy":           privacy,
        "SortMethod":        "Name",
        "SortDirection":     "Ascending",
    }
    resp, err = signed_request("POST", url, body=body)
    if err:
        return None, err
    node = resp.get("Response", {}).get("Node", {})
    return node, None


def get_album_key(node):
    """Extract AlbumKey from a node's Uris if it's an Album type."""
    album_uri = node.get("Uris", {}).get("Album", {}).get("Uri", "")
    if album_uri:
        return album_uri.split("/")[-1]
    return ""


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(node_id=None):
    if node_id is None:
        print("Fetching root node...")
        root, err = get_root_node()
        if err:
            print(f"ERROR: {err}")
            sys.exit(1)
        node_id = root

    print(f"Children of node {node_id}:\n")
    nodes, err = list_children(node_id)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)

    print(f"{'Node ID':<14} {'Type':<8} {'Name'}")
    print("─" * 55)
    for n in nodes:
        nid   = n.get("NodeID", "")
        ntype = n.get("Type", "")
        nname = n.get("Name", "")
        album_key = get_album_key(n) if ntype == "Album" else ""
        suffix = f"  [AlbumKey: {album_key}]" if album_key else ""
        print(f"{nid:<14} {ntype:<8} {nname}{suffix}")
    print()


def cmd_create():
    print("Fetching root node...")
    root, err = get_root_node()
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)
    print(f"Root node: {root}\n")

    # Map name → node_id for resolving parent references
    name_to_node = {}

    for parent_ref, node_type, name, privacy in STRUCTURE:
        if parent_ref is None:
            parent_id = root
        else:
            parent_id = name_to_node.get(parent_ref)
            if not parent_id:
                print(f"  ERROR — parent '{parent_ref}' not yet created. Check STRUCTURE order.")
                sys.exit(1)

        print(f"Creating {node_type}: '{name}' under node {parent_id}...")
        node, err = create_node(parent_id, node_type, name, privacy)
        if err:
            print(f"  ERROR: {err}")
            sys.exit(1)

        node_id   = node.get("NodeID", "")
        album_key = get_album_key(node) if node_type == "Album" else ""
        web_uri   = node.get("WebUri", "")

        name_to_node[name] = node_id

        print(f"  OK — NodeID: {node_id}", end="")
        if album_key:
            print(f"  |  AlbumKey: {album_key}", end="")
        print(f"\n     URL: {web_uri}")

    print("\n─ Done. Final structure:\n")
    # Print summary
    for parent_ref, node_type, name, privacy in STRUCTURE:
        nid = name_to_node.get(name, "?")
        indent = "    " if parent_ref is not None else ""
        print(f"{indent}[{node_type}] {name}  (NodeID: {nid})")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--list" in args:
        args.remove("--list")
        node_id = args[0] if args else None
        cmd_list(node_id)
    else:
        cmd_create()


if __name__ == "__main__":
    main()
