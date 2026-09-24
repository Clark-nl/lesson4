# TikTok upload automation

Direct integration with TikTok's Content Posting API (v2), built because
Higgsfield's MCP `tiktok_publish` tool requires an interactive consent
widget that this coding session's client doesn't support — that gate is a
deliberate TikTok compliance requirement (Music Usage Confirmation, AIGC
labeling, privacy/interaction choices), not something to route around. This
folder is a legitimate, separate path: **one real human login, one time**,
then fully scripted uploads after that.

## What this does and doesn't solve

- ✅ After the one-time setup below, `upload_video.py` uploads a video with
  no further manual login — safe to call from a cron job, n8n, CI, etc.
- ❌ It does **not** bypass TikTok's own review process. New apps start
  **unaudited**: the API will reject `PUBLIC_TO_EVERYONE` posts from an
  unaudited app (`unaudited_client_can_not_post_to_public`). Until your app
  passes TikTok's audit, use `--privacy SELF_ONLY` (private) or accept that
  posts land as drafts in the TikTok inbox for manual completion. Apply for
  audit in the TikTok developer portal to unlock public Direct Post — this
  is TikTok's own policy and cannot be scripted around.
- ❌ It does not solve YouTube. That's a separate, unrelated platform/API.

## One-time setup (you do this, not Claude)

1. Go to <https://developers.tiktok.com/>, create an app.
2. Add the **Content Posting API** product to the app.
3. Add scope `video.publish`.
4. Under app settings, add a redirect URI. The default this script expects
   is `http://localhost:8787/callback` — you can change it, just keep
   `TIKTOK_REDIRECT_URI` in `.env` matching what's registered in the portal.
5. Copy the **Client Key** and **Client Secret** into a local `.env`:
   ```
   cp .env.example .env
   # edit .env and fill in TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET
   ```
6. Run the one-time interactive login (needs a real browser + real network
   access — run this on your own machine, not inside a restricted sandbox):
   ```
   python3 oauth_setup.py
   ```
   This opens an authorization URL for you to approve in a browser, catches
   the redirect locally, exchanges the code for tokens, and saves a
   `TIKTOK_REFRESH_TOKEN` into `.env`. You will not need to log in again —
   refresh tokens are long-lived and the upload script auto-renews access
   tokens.

## Ongoing automated use

```
python3 upload_video.py "<video_url>" \
  --title "Where Is My Bubble? Circle, Triangle, Star for Kids" \
  --description "Lumi the jellyfish loses her round bubble..." \
  --privacy SELF_ONLY
```

- `<video_url>` can be any publicly reachable mp4 URL, including a
  Higgsfield-hosted result URL.
- Swap `--privacy SELF_ONLY` for `PUBLIC_TO_EVERYONE` once your app is
  audited.
- Wire this into `n8n-workflows/higgsfield-blotato-daily-video.json` or a
  cron job for full "generate → publish" automation once the one-time login
  above is done.

## Secrets

`.env` is git-ignored (see repo root `.gitignore`). Never commit it. Nothing
in this repo logs or prints your client secret or tokens.
