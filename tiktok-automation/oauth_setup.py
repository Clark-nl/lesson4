#!/usr/bin/env python3
"""
One-time TikTok OAuth setup.

Run this ONCE, interactively, on a machine with a real browser and real
internet access (NOT inside a restricted/sandboxed session). It opens a
tiny local HTTP server to catch TikTok's OAuth redirect, exchanges the
authorization code for an access token + refresh token, and saves the
refresh token to .env so upload_video.py can run unattended afterward.

Prerequisites (do these on https://developers.tiktok.com/ first):
  1. Create an app, add the "Content Posting API" product.
  2. Add scope: video.publish (and video.upload if you want draft-only
     posting instead of direct publish).
  3. Set a redirect URI matching TIKTOK_REDIRECT_URI below
     (default http://localhost:8787/callback).
  4. Copy the Client Key and Client Secret into .env (see .env.example).
  5. Note: until TikTok reviews and approves your app, it stays in
     "sandbox"/unaudited mode, which can only post as unlisted/SELF_ONLY
     drafts, not public posts. Apply for audit in the developer portal to
     unlock public Direct Post.

Usage:
  cp .env.example .env   # fill in TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET
  python3 oauth_setup.py
"""
import base64
import hashlib
import http.server
import os
import secrets
import sys
import urllib.parse
import urllib.request
import json

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_env(updates: dict):
    env = load_env()
    env.update(updates)
    with open(ENV_PATH, "w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")


def make_pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def main():
    env = load_env()
    client_key = env.get("TIKTOK_CLIENT_KEY") or os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = env.get("TIKTOK_CLIENT_SECRET") or os.environ.get("TIKTOK_CLIENT_SECRET")
    redirect_uri = env.get("TIKTOK_REDIRECT_URI") or "http://localhost:8787/callback"

    if not client_key or not client_secret:
        print("Missing TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET.")
        print(f"Copy .env.example to .env in {os.path.dirname(__file__)} and fill them in first.")
        sys.exit(1)

    state = secrets.token_hex(16)
    verifier, challenge = make_pkce_pair()

    auth_params = {
        "client_key": client_key,
        "scope": "video.publish",
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(auth_params)

    print("\n1. Open this URL in a browser and log in / authorize:\n")
    print(auth_url)
    print("\n2. After you approve, TikTok redirects to your redirect_uri with ?code=...")
    print("   Waiting for that redirect on", redirect_uri, "...\n")

    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    host = parsed_redirect.hostname or "localhost"
    port = parsed_redirect.port or 8787
    callback_path = parsed_redirect.path or "/callback"

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != callback_path:
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            code = qs.get("code", [None])[0]
            got_state = qs.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if not code or got_state != state:
                self.wfile.write("Auth failed or state mismatch. Check the terminal and retry.".encode())
                return
            result["code"] = code
            self.wfile.write("Authorized. You can close this tab and return to the terminal.".encode())

        def log_message(self, *args):
            pass  # keep terminal output clean

    server = http.server.HTTPServer((host, port), Handler)
    while "code" not in result:
        server.handle_request()
    server.server_close()

    code = result["code"]

    token_req = urllib.request.Request(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data=urllib.parse.urlencode({
            "client_key": client_key,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        method="POST",
    )
    with urllib.request.urlopen(token_req) as resp:
        token_data = json.loads(resp.read().decode())

    if "access_token" not in token_data:
        print("Token exchange failed:", token_data)
        sys.exit(1)

    save_env({
        "TIKTOK_CLIENT_KEY": client_key,
        "TIKTOK_CLIENT_SECRET": client_secret,
        "TIKTOK_REDIRECT_URI": redirect_uri,
        "TIKTOK_REFRESH_TOKEN": token_data["refresh_token"],
        "TIKTOK_OPEN_ID": token_data.get("open_id", ""),
    })

    print("\nDone. Saved refresh token to", ENV_PATH)
    print("From now on, run upload_video.py directly with no further login needed")
    print("(refresh tokens are long-lived and this script auto-refreshes access tokens).")


if __name__ == "__main__":
    main()
