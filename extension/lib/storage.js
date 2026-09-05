// 공용 storage 헬퍼. background/popup/options에서 동일하게 사용.
const DEFAULTS = {
  isPremium: false,
  licenseKey: "",
  timer: {
    running: false,
    mode: "focus", // "focus" | "break"
    endsAt: null,
    focusMinutes: 25,
    breakMinutes: 5,
  },
  stats: {
    sessionsCompleted: 0,
    focusSecondsToday: 0,
    lastActiveDate: null,
  },
  autoCleanup: {
    enabled: false, // 프리미엄 전용
    idleMinutes: 60,
  },
};

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

async function getAll() {
  const stored = await chrome.storage.local.get(Object.keys(DEFAULTS));
  const merged = { ...DEFAULTS, ...stored };
  // 자정 넘어가면 오늘 통계 리셋
  if (merged.stats.lastActiveDate !== todayKey()) {
    merged.stats = { ...merged.stats, focusSecondsToday: 0, lastActiveDate: todayKey() };
    await chrome.storage.local.set({ stats: merged.stats });
  }
  return merged;
}

async function set(patch) {
  await chrome.storage.local.set(patch);
}

async function getPremiumFlag() {
  const { isPremium = false } = await chrome.storage.sync.get(["isPremium"]);
  return isPremium;
}

async function setPremiumFlag(value) {
  await chrome.storage.sync.set({ isPremium: value });
}

export { DEFAULTS, getAll, set, getPremiumFlag, setPremiumFlag, todayKey };
