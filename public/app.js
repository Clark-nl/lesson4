(() => {
  const qs = new URLSearchParams(location.search);
  const shopFromUrl = qs.get('shop');
  const connected = qs.get('connected') === '1';

  const el = {
    connectForm: document.getElementById('connect-form'),
    shopInput: document.getElementById('shop'),
    connectStatus: document.getElementById('connect-status'),
    builderPanel: document.getElementById('builder-panel'),
    previewPanel: document.getElementById('preview-panel'),
    productList: document.getElementById('product-list'),
    selectedCount: document.getElementById('selected-count'),
    refreshBtn: document.getElementById('refresh-products'),
    buildBtn: document.getElementById('build-btn'),
    buildStatus: document.getElementById('build-status'),
    storeName: document.getElementById('storeName'),
    tagline: document.getElementById('tagline'),
    theme: document.getElementById('theme'),
    previewFrame: document.getElementById('preview-frame'),
    downloadBtn: document.getElementById('download-btn'),
  };

  const state = {
    shop: shopFromUrl || '',
    products: [],
    selected: new Set(),
    lastHtml: '',
  };

  function setStatus(node, message, kind) {
    node.textContent = message || '';
    node.className = 'status' + (kind ? ` ${kind}` : '');
  }

  el.connectForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const shop = el.shopInput.value.trim();
    if (!shop) return;
    location.href = `/auth?shop=${encodeURIComponent(shop)}`;
  });

  async function init() {
    if (!state.shop) return;
    el.shopInput.value = state.shop;

    const res = await fetch(`/api/status?shop=${encodeURIComponent(state.shop)}`);
    const { connected: isConnected } = await res.json();

    if (!isConnected) {
      setStatus(el.connectStatus, connected ? '연동에 실패했습니다. 다시 시도해주세요.' : '', 'error');
      return;
    }

    setStatus(el.connectStatus, `✅ ${state.shop} 연동 완료`, 'ok');
    el.builderPanel.classList.remove('hidden');
    await loadProducts();
  }

  async function loadProducts() {
    setStatus(el.buildStatus, '상품을 불러오는 중...');
    try {
      const res = await fetch(`/api/products?shop=${encodeURIComponent(state.shop)}&first=30`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '상품을 불러오지 못했습니다.');
      state.products = data.products;
      renderProducts();
      setStatus(el.buildStatus, `${state.products.length}개 상품을 불러왔습니다.`, 'ok');
    } catch (err) {
      setStatus(el.buildStatus, err.message, 'error');
    }
  }

  function renderProducts() {
    el.productList.innerHTML = '';
    state.products.forEach((p) => {
      const card = document.createElement('div');
      card.className = 'product-card' + (state.selected.has(p.id) ? ' selected' : '');
      card.innerHTML = `
        ${p.image ? `<img src="${p.image}" alt="${p.imageAlt}" loading="lazy" />` : `<div class="ph">이미지 없음</div>`}
        <div class="info">
          <h4>${p.title}</h4>
          <p class="price">${p.price ? `${p.price} ${p.currency}` : ''}</p>
        </div>
      `;
      card.addEventListener('click', () => toggleSelect(p.id, card));
      el.productList.appendChild(card);
    });
    updateSelectedCount();
  }

  function toggleSelect(id, card) {
    if (state.selected.has(id)) {
      state.selected.delete(id);
      card.classList.remove('selected');
    } else {
      state.selected.add(id);
      card.classList.add('selected');
    }
    updateSelectedCount();
  }

  function updateSelectedCount() {
    el.selectedCount.textContent = `${state.selected.size}개 선택됨`;
    el.buildBtn.disabled = state.selected.size === 0;
  }

  el.refreshBtn.addEventListener('click', loadProducts);

  el.buildBtn.addEventListener('click', async () => {
    setStatus(el.buildStatus, '페이지 생성 중...');
    try {
      const res = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          shop: state.shop,
          storeName: el.storeName.value,
          tagline: el.tagline.value,
          theme: el.theme.value,
          productIds: Array.from(state.selected),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '생성에 실패했습니다.');

      state.lastHtml = data.html;
      el.previewFrame.srcdoc = data.html;
      el.previewPanel.classList.remove('hidden');
      setStatus(el.buildStatus, '생성 완료! 아래에서 미리보기를 확인하세요.', 'ok');
      el.previewPanel.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      setStatus(el.buildStatus, err.message, 'error');
    }
  });

  el.downloadBtn.addEventListener('click', () => {
    if (!state.lastHtml) return;
    const blob = new Blob([state.lastHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(el.storeName.value || 'store').replace(/\s+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
  });

  init();
})();
