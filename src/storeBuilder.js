const THEMES = {
  light: { bg: '#ffffff', fg: '#1a1a1a', accent: '#1a73e8', card: '#f7f7f8' },
  dark: { bg: '#121212', fg: '#f5f5f5', accent: '#8ab4f8', card: '#1e1e1e' },
  mint: { bg: '#fbfffe', fg: '#0f2b25', accent: '#00b894', card: '#eafff8' },
};

function escapeHtml(str = '') {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatPrice(price, currency) {
  if (price == null) return '';
  const amount = Number(price).toFixed(2);
  return `${amount} ${currency || ''}`.trim();
}

// 선택된 Shopify 상품 데이터로 정적 스토어 랜딩 페이지 HTML을 생성한다.
function buildStorePage({ storeName, tagline, products, theme = 'light', storeUrl }) {
  const palette = THEMES[theme] || THEMES.light;
  const safeName = escapeHtml(storeName || '내 쇼핑몰');
  const safeTagline = escapeHtml(tagline || '');

  const cards = products
    .map((p) => {
      const img = p.image
        ? `<img src="${escapeHtml(p.image)}" alt="${escapeHtml(p.imageAlt || p.title)}" loading="lazy" />`
        : `<div class="placeholder">No Image</div>`;
      const link = storeUrl && p.handle ? `https://${storeUrl}/products/${escapeHtml(p.handle)}` : '#';
      return `
        <a class="card" href="${link}" target="_blank" rel="noopener noreferrer">
          <div class="card-img">${img}</div>
          <div class="card-body">
            <h3>${escapeHtml(p.title)}</h3>
            <p class="price">${formatPrice(p.price, p.currency)}</p>
          </div>
        </a>`;
    })
    .join('\n');

  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${safeName}</title>
<style>
  :root {
    --bg: ${palette.bg}; --fg: ${palette.fg}; --accent: ${palette.accent}; --card: ${palette.card};
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg); font-family: -apple-system, "Pretendard", "Apple SD Gothic Neo", sans-serif; }
  header { padding: 64px 24px; text-align: center; }
  header h1 { font-size: 2.4rem; margin: 0 0 8px; }
  header p { opacity: 0.7; margin: 0; }
  main { max-width: 1100px; margin: 0 auto; padding: 0 24px 64px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
  .card { display: block; background: var(--card); border-radius: 14px; overflow: hidden; text-decoration: none; color: inherit; transition: transform .15s ease; }
  .card:hover { transform: translateY(-4px); }
  .card-img { aspect-ratio: 1 / 1; background: #ddd; display: flex; align-items: center; justify-content: center; }
  .card-img img { width: 100%; height: 100%; object-fit: cover; }
  .placeholder { color: #888; font-size: 0.85rem; }
  .card-body { padding: 14px 16px; }
  .card-body h3 { font-size: 1rem; margin: 0 0 6px; }
  .price { margin: 0; font-weight: 600; color: var(--accent); }
  footer { text-align: center; padding: 32px; opacity: 0.5; font-size: 0.8rem; }
</style>
</head>
<body>
  <header>
    <h1>${safeName}</h1>
    <p>${safeTagline}</p>
  </header>
  <main>
    <div class="grid">
      ${cards || '<p style="text-align:center; opacity:.6;">선택된 상품이 없습니다.</p>'}
    </div>
  </main>
  <footer>Powered by Shopify 연동 빌더</footer>
</body>
</html>`;
}

module.exports = { buildStorePage, THEMES: Object.keys(THEMES) };
