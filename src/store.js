// 데모/학습용 인메모리 세션 저장소.
// 운영 환경에서는 Redis, DB 등 영속 저장소로 교체해야 합니다.
const sessions = new Map(); // shop -> { accessToken, scope, installedAt }
const oauthStates = new Map(); // state -> { shop, expiresAt }

function saveSession(shop, data) {
  sessions.set(shop, { ...data, installedAt: new Date().toISOString() });
}

function getSession(shop) {
  return sessions.get(shop);
}

function saveState(state, shop) {
  oauthStates.set(state, { shop, expiresAt: Date.now() + 5 * 60 * 1000 });
}

function consumeState(state) {
  const entry = oauthStates.get(state);
  oauthStates.delete(state);
  if (!entry || entry.expiresAt < Date.now()) return null;
  return entry.shop;
}

module.exports = { saveSession, getSession, saveState, consumeState };
