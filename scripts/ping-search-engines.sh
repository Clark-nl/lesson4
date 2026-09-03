#!/usr/bin/env bash
# Notifies search engines about a new/updated sitemap.
# Usage: ping-search-engines.sh <sitemap_url> [indexnow_key]
#
# Google reads a simple ping URL. Bing, Naver, Yandex and Seznam all accept
# the shared IndexNow protocol, so one call covers all of them provided a
# key file has been published at https://<domain>/<key>.txt.

set -euo pipefail

SITEMAP_URL="${1:?Usage: ping-search-engines.sh <sitemap_url> [indexnow_key]}"
INDEXNOW_KEY="${2:-${INDEXNOW_KEY:-}}"

HOST="$(echo "$SITEMAP_URL" | sed -E 's#^[a-zA-Z]+://##; s#/.*##')"

echo "== Pinging Google =="
curl -fsS -o /dev/null -w 'Google ping HTTP %{http_code}\n' \
  "https://www.google.com/ping?sitemap=${SITEMAP_URL}" || echo "Google ping failed"

if [ -n "$INDEXNOW_KEY" ]; then
  echo "== Submitting to IndexNow (Bing, Naver, Yandex, Seznam) =="
  curl -fsS -X POST "https://api.indexnow.org/indexnow" \
    -H "Content-Type: application/json" \
    -d "{\"host\":\"${HOST}\",\"key\":\"${INDEXNOW_KEY}\",\"keyLocation\":\"https://${HOST}/${INDEXNOW_KEY}.txt\",\"urlList\":[\"${SITEMAP_URL}\"]}" \
    -w '\nIndexNow submit HTTP %{http_code}\n' || echo "IndexNow submit failed"
else
  echo "== Skipping IndexNow: no key provided (set INDEXNOW_KEY or pass as 2nd arg) =="
fi
