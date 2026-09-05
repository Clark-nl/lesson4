import { getAll, set } from "./lib/storage.js";
import { isPremium } from "./lib/premium.js";

const SESSION_END_ALARM = "focus-session-end";
const IDLE_CHECK_ALARM = "idle-tab-check";

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(IDLE_CHECK_ALARM, { periodInMinutes: 10 });
});

// ---- 타이머 ----
// 정확도를 위해 1초 폴링 대신 endsAt 타임스탬프 하나로 상태를 표현하고,
// 세션 종료 시점에 정확히 한 번 알람을 건다. 팝업은 열려 있는 동안
// endsAt을 기준으로 스스로 카운트다운을 그려서 UI 갱신은 background에 의존하지 않는다.

async function startTimer(mode) {
  const state = await getAll();
  const minutes = mode === "break" ? state.timer.breakMinutes : state.timer.focusMinutes;
  const totalMs = minutes * 60 * 1000;
  const endsAt = Date.now() + totalMs;

  await set({ timer: { ...state.timer, running: true, mode, endsAt, remainingMs: null } });
  chrome.alarms.create(SESSION_END_ALARM, { when: endsAt });
}

async function resumeTimer() {
  const state = await getAll();
  if (!state.timer.remainingMs) return;
  const endsAt = Date.now() + state.timer.remainingMs;
  await set({ timer: { ...state.timer, running: true, endsAt, remainingMs: null } });
  chrome.alarms.create(SESSION_END_ALARM, { when: endsAt });
}

async function pauseTimer() {
  const state = await getAll();
  const remainingMs = Math.max(0, (state.timer.endsAt || Date.now()) - Date.now());
  await set({ timer: { ...state.timer, running: false, endsAt: null, remainingMs } });
  chrome.alarms.clear(SESSION_END_ALARM);
}

async function resetTimer() {
  const state = await getAll();
  await set({ timer: { ...state.timer, running: false, endsAt: null, remainingMs: null } });
  chrome.alarms.clear(SESSION_END_ALARM);
}

async function onSessionEnd() {
  const state = await getAll();
  const finishedMode = state.timer.mode;

  if (finishedMode === "focus") {
    await set({
      stats: {
        ...state.stats,
        sessionsCompleted: state.stats.sessionsCompleted + 1,
        focusSecondsToday: state.stats.focusSecondsToday + state.timer.focusMinutes * 60,
      },
    });
  }

  await set({ timer: { ...state.timer, running: false, endsAt: null, remainingMs: null } });

  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: finishedMode === "focus" ? "집중 세션 완료!" : "휴식 종료",
    message:
      finishedMode === "focus"
        ? "잘하셨어요. 짧은 휴식을 가져보세요."
        : "휴식이 끝났습니다. 다시 집중해볼까요?",
  });
}

// ---- 탭 정리 ----

async function closeDuplicateTabs() {
  const tabs = await chrome.tabs.query({});
  const seen = new Set();
  const toClose = [];

  for (const tab of tabs) {
    if (!tab.url || tab.pinned) continue;
    if (seen.has(tab.url)) {
      toClose.push(tab.id);
    } else {
      seen.add(tab.url);
    }
  }

  if (toClose.length) {
    await chrome.tabs.remove(toClose);
  }
  return toClose.length;
}

async function groupTabsByDomain() {
  const premium = await isPremium();
  if (!premium) return { ok: false, reason: "premium_required" };

  const tabs = await chrome.tabs.query({ currentWindow: true, pinned: false });
  const byDomain = new Map();
  for (const tab of tabs) {
    if (!tab.url) continue;
    let host;
    try {
      host = new URL(tab.url).hostname.replace(/^www\./, "");
    } catch {
      continue;
    }
    if (!byDomain.has(host)) byDomain.set(host, []);
    byDomain.get(host).push(tab.id);
  }

  let groupsCreated = 0;
  for (const [host, ids] of byDomain.entries()) {
    if (ids.length < 2) continue;
    const groupId = await chrome.tabs.group({ tabIds: ids });
    await chrome.tabGroups.update(groupId, { title: host });
    groupsCreated += 1;
  }
  return { ok: true, groups: groupsCreated };
}

async function checkIdleTabs() {
  const state = await getAll();
  const premium = await isPremium();
  if (!premium || !state.autoCleanup.enabled) return;

  const idleMs = state.autoCleanup.idleMinutes * 60 * 1000;
  const cutoff = Date.now() - idleMs;
  const tabs = await chrome.tabs.query({ currentWindow: true, pinned: false, active: false });
  const toClose = tabs.filter((t) => t.lastAccessed && t.lastAccessed < cutoff).map((t) => t.id);
  if (toClose.length) {
    await chrome.tabs.remove(toClose);
  }
}

// ---- 메시지 라우팅 ----

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    switch (msg?.type) {
      case "timer:start":
        await startTimer(msg.mode || "focus");
        sendResponse({ ok: true });
        break;
      case "timer:resume":
        await resumeTimer();
        sendResponse({ ok: true });
        break;
      case "timer:pause":
        await pauseTimer();
        sendResponse({ ok: true });
        break;
      case "timer:reset":
        await resetTimer();
        sendResponse({ ok: true });
        break;
      case "tabs:closeDuplicates": {
        const closed = await closeDuplicateTabs();
        sendResponse({ ok: true, closed });
        break;
      }
      case "tabs:groupByDomain": {
        const result = await groupTabsByDomain();
        sendResponse(result);
        break;
      }
      default:
        sendResponse({ ok: false, error: "unknown_message" });
    }
  })();
  return true; // async 응답을 위해 채널을 열어둠
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === SESSION_END_ALARM) onSessionEnd();
  if (alarm.name === IDLE_CHECK_ALARM) checkIdleTabs();
});
