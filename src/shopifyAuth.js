const crypto = require('crypto');

const SHOP_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9-]*\.myshopify\.com$/;

function isValidShop(shop) {
  return typeof shop === 'string' && SHOP_REGEX.test(shop);
}

function buildAuthUrl({ shop, apiKey, scopes, redirectUri, state }) {
  const url = new URL(`https://${shop}/admin/oauth/authorize`);
  url.searchParams.set('client_id', apiKey);
  url.searchParams.set('scope', scopes);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('state', state);
  return url.toString();
}

// Shopify OAuth 콜백 쿼리스트링의 hmac 파라미터를 검증한다.
// https://shopify.dev/docs/apps/auth/oauth/getting-started#step-5-confirm-installation
function verifyHmac(query, apiSecret) {
  const { hmac, signature, ...rest } = query;
  if (!hmac) return false;

  const message = Object.keys(rest)
    .sort()
    .map((key) => `${key}=${Array.isArray(rest[key]) ? rest[key].join(',') : rest[key]}`)
    .join('&');

  const digest = crypto.createHmac('sha256', apiSecret).update(message).digest('hex');

  const digestBuf = Buffer.from(digest, 'utf8');
  const hmacBuf = Buffer.from(String(hmac), 'utf8');
  if (digestBuf.length !== hmacBuf.length) return false;
  return crypto.timingSafeEqual(digestBuf, hmacBuf);
}

async function exchangeCodeForToken({ shop, apiKey, apiSecret, code }) {
  const res = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: apiKey, client_secret: apiSecret, code }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`토큰 교환 실패 (${res.status}): ${text}`);
  }

  return res.json(); // { access_token, scope }
}

module.exports = { isValidShop, buildAuthUrl, verifyHmac, exchangeCodeForToken };
