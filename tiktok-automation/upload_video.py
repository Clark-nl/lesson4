#!/usr/bin/env python3
"""
Automated TikTok upload via the Content Posting API (v2), using the
refresh token saved by oauth_setup.py. No interactive login needed once
that one-time setup has run.

IMPORTANT — read before relying on this for public posts:
TikTok apps start in an unaudited/sandbox state. Until TikTok's developer
portal marks your app as audited for the Content Posting API, uploads can
only be posted as private/self-only drafts (the API rejects
PUBLIC_TO_EVERYONE for unaudited apps) or delivered to the user's TikTok
inbox as a draft to finish manually. Apply for audit in the developer
portal to unlock direct public posting. This script does not and cannot
bypass that — it is a TikTok platform policy enforced server-side.

Usage:
  python3 upload_video.py <video_url> \\
      --title "Where Is My Bubble? Circle, Triangle, Star for Kids" \\
      --description "..." \\
      --privacy SELF_ONLY   # or PUBLIC_TO_EVERYONE once your app is audited

Run this on a machine with real, unrestricted internet access to both the
video's source host and TikTok's API — not inside a network-restricted
sandbox.
"""
import argparse
import json
import os
import sys
import tempfile
import urllib.request
import urllib.parse

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
API_BASE = "https://open.tiktokapis.com/v2"


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


def api_post(path, access_token, payload):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def refresh_access_token(env):
    req = urllib.request.Request(
        f"{API_BASE}/oauth/token/",
        data=urllib.parse.urlencode({
            "client_key": env["TIKTOK_CLIENT_KEY"],
            "client_secret": env["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": env["TIKTOK_REFRESH_TOKEN"],
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    if "access_token" not in data:
        print("Token refresh failed:", data)
        sys.exit(1)
    # TikTok may rotate the refresh token; persist the latest one.
    if data.get("refresh_token"):
        save_env({"TIKTOK_REFRESH_TOKEN": data["refresh_token"]})
    return data["access_token"]


def download_video(url):
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    with urllib.request.urlopen(url) as resp:
        tmp.write(resp.read())
    tmp.close()
    return tmp.name


def upload_video(video_url, title, description, privacy_level, allow_comment, allow_duet, allow_stitch, is_aigc):
    env = load_env()
    required = ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        print("Missing from .env:", ", ".join(missing))
        print("Run oauth_setup.py once first.")
        sys.exit(1)

    access_token = refresh_access_token(env)

    print("Downloading source video...")
    local_path = download_video(video_url)
    video_size = os.path.getsize(local_path)
    print(f"Downloaded {video_size} bytes.")

    chunk_size = min(video_size, 64 * 1024 * 1024)  # single chunk if <=64MB
    total_chunk_count = 1 if video_size <= 64 * 1024 * 1024 else -(-video_size // chunk_size)

    init_payload = {
        "post_info": {
            "title": title,
            "description": description,
            "privacy_level": privacy_level,
            "disable_duet": not allow_duet,
            "disable_comment": not allow_comment,
            "disable_stitch": not allow_stitch,
            "video_cover_timestamp_ms": 1000,
            "is_aigc": is_aigc,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunk_count,
        },
    }
    print("Initializing upload...")
    init_resp = api_post("/post/publish/video/init/", access_token, init_payload)
    if "data" not in init_resp or "publish_id" not in init_resp["data"]:
        print("Init failed:", init_resp)
        print("If error.code is 'unaudited_client_can_not_post_to_public', your app is")
        print("not yet audited by TikTok for public posting — retry with --privacy SELF_ONLY")
        print("or complete the app audit in the TikTok developer portal.")
        sys.exit(1)

    publish_id = init_resp["data"]["publish_id"]
    upload_url = init_resp["data"]["upload_url"]

    print("Uploading video bytes...")
    with open(local_path, "rb") as f:
        data = f.read()
    put_req = urllib.request.Request(
        upload_url,
        data=data,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        method="PUT",
    )
    urllib.request.urlopen(put_req)
    os.unlink(local_path)

    print("Upload sent. Polling publish status...")
    import time
    for _ in range(30):
        status_resp = api_post("/post/publish/status/fetch/", access_token, {"publish_id": publish_id})
        status = status_resp.get("data", {}).get("status")
        print("  status:", status)
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            print(json.dumps(status_resp, indent=2))
            return status_resp
        time.sleep(5)
    print("Timed out waiting for publish status; check the TikTok app/developer portal.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_url")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--privacy", default="SELF_ONLY",
                         choices=["SELF_ONLY", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "PUBLIC_TO_EVERYONE"],
                         help="Defaults to SELF_ONLY since most apps start unaudited. Use PUBLIC_TO_EVERYONE only once your app is audited for public posting.")
    parser.add_argument("--no-comment", action="store_true")
    parser.add_argument("--no-duet", action="store_true")
    parser.add_argument("--no-stitch", action="store_true")
    parser.add_argument("--not-aigc", action="store_true", help="Only pass this if the content is genuinely NOT AI-generated.")
    args = parser.parse_args()

    upload_video(
        video_url=args.video_url,
        title=args.title,
        description=args.description,
        privacy_level=args.privacy,
        allow_comment=not args.no_comment,
        allow_duet=not args.no_duet,
        allow_stitch=not args.no_stitch,
        is_aigc=not args.not_aigc,
    )


if __name__ == "__main__":
    main()
