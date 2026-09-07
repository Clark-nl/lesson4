require('dotenv').config();
const crypto = require('crypto');
const path = require('path');
const express = require('express');
const cookieParser = require('cookie-parser');

const { isValidShop, buildAuthUrl, verifyHmac, exchangeCodeForToken } = require('./shopifyAuth');
const { fetchShopInfo, fetchProducts } = require('./shopifyClient');
const { buildStorePage, THEMES } = require('./storeBuilder');
const { saveSession, getSession, saveState, consumeState } = require('./store');

const { SHOPIFY_API_KEY, SHOPIFY_API_SECRET, SCOPES, HOST, PORT, COOKIE_SECRET } = process.env;

if (!SHOPIFY_API_KEY || !SHOPIFY_API_SECRET || !HOST) {
  console.warn(
    '[경고] SHOPIFY_API_KEY / SHOPIFY_API_SECRET / HOST 환경변수가 설정되지 않았습니다. ' +
      '.env.example을 복사해 .env를 만들고 값을 채워주세요. (Shopify OAuth 연동에 필요)'
  );
}

const app = express();
app.use(express.json());
app.use(cookieParser(COOKIE_SECRET || 'dev-secret'));
app.use(express.static(path.join(__dirname, '..', 'public')));

function requireSession(req, res, next) {
  const shop = req.query.shop || req.body.shop;
  if (!isValidShop(shop)) {
    return res.status(400).json({ error: '유효하지 않은 shop 파라미터입니다.' });
  }
  const session = getSession(shop);
  if (!session) {
    return res.status(401).json({ error: '해당 스토어가 아직 연동되지 않았습니다. 먼저 /auth 로 설치를 진행하세요.' });
  }
  req.shop = shop;
  req.shopSession = session;
  next();
}

// 1) 앱 설치 시작 - Shopify OAuth 인가 화면으로 리다이렉트
app.get('/auth', (req, res) => {
  const shop = req.query.shop;
  if (!isValidShop(shop)) {
    return res.status(400).send('유효한 shop 파라미터가 필요합니다. 예: /auth?shop=your-store.myshopify.com');
  }

  const state = crypto.randomBytes(16).toString('hex');
  saveState(state, shop);

  const redirectUri = `${HOST}/auth/callback`;
  const authUrl = buildAuthUrl({
    shop,
    apiKey: SHOPIFY_API_KEY,
    scopes: SCOPES || 'read_products',
    redirectUri,
    state,
  });

  res.cookie('shopify_oauth_state', state, { httpOnly: true, sameSite: 'lax', signed: true });
  res.redirect(authUrl);
});

// 2) OAuth 콜백 - HMAC/state 검증 후 access token 교환
app.get('/auth/callback', async (req, res) => {
  try {
    const { shop, code, state } = req.query;

    if (!isValidShop(shop)) {
      return res.status(400).send('유효하지 않은 shop 파라미터입니다.');
    }
    if (!verifyHmac(req.query, SHOPIFY_API_SECRET)) {
      return res.status(401).send('HMAC 검증에 실패했습니다. 요청이 변조되었을 수 있습니다.');
    }
    const expectedShop = consumeState(state);
    if (!expectedShop || expectedShop !== shop) {
      return res.status(401).send('state 값이 일치하지 않습니다 (CSRF 방지). 설치를 다시 시도해주세요.');
    }

    const { access_token: accessToken, scope } = await exchangeCodeForToken({
      shop,
      apiKey: SHOPIFY_API_KEY,
      apiSecret: SHOPIFY_API_SECRET,
      code,
    });

    saveSession(shop, { accessToken, scope });

    res.redirect(`/?shop=${encodeURIComponent(shop)}&connected=1`);
  } catch (err) {
    console.error(err);
    res.status(500).send(`연동 중 오류가 발생했습니다: ${err.message}`);
  }
});

// 연동 상태 확인 (프론트엔드가 최초 진입 시 호출)
app.get('/api/status', (req, res) => {
  const shop = req.query.shop;
  if (!isValidShop(shop)) return res.json({ connected: false });
  res.json({ connected: Boolean(getSession(shop)) });
});

app.get('/api/shop', requireSession, async (req, res) => {
  try {
    const shopInfo = await fetchShopInfo(req.shop, req.shopSession.accessToken);
    res.json(shopInfo);
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/products', requireSession, async (req, res) => {
  try {
    const first = Math.min(Number(req.query.first) || 20, 50);
    const products = await fetchProducts(req.shop, req.shopSession.accessToken, first);
    res.json({ products });
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: err.message });
  }
});

// 선택된 상품으로 정적 스토어 페이지 HTML 생성
app.post('/api/build', requireSession, async (req, res) => {
  try {
    const { storeName, tagline, theme, productIds } = req.body;
    if (!Array.isArray(productIds) || productIds.length === 0) {
      return res.status(400).json({ error: '최소 1개 이상의 상품을 선택해주세요.' });
    }

    const allProducts = await fetchProducts(req.shop, req.shopSession.accessToken, 50);
    const selected = allProducts.filter((p) => productIds.includes(p.id));

    const html = buildStorePage({
      storeName,
      tagline,
      theme: THEMES.includes(theme) ? theme : 'light',
      products: selected,
      storeUrl: req.shop,
    });

    res.json({ html });
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/themes', (req, res) => res.json({ themes: THEMES }));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

const port = PORT || 3000;
app.listen(port, () => {
  console.log(`Shopify 연동 빌더 서버 실행 중: http://localhost:${port}`);
});
