import { getAll } from "./lib/storage.js";
import { isPremium } from "./lib/premium.js";

const timeDisplay = document.getElementById("timeDisplay");
const modeLabel = document.getElementById("modeLabel");
const startBtn = document.getElementById("startBtn");
const pauseBtn = document.getElementById("pauseBtn");
const resumeBtn = document.getElementById("resumeBtn");
const resetBtn = document.getElementById("resetBtn");
const startBreakBtn = document.getElementById("startBreakBtn");
const tabCountLabel = document.getElementById("tabCountLabel");
const closeDuplicatesBtn = document.getElementById("closeDuplicatesBtn");
const groupByDomainBtn = document.getElementById("groupByDomainBtn");
const premiumBadge = document.getElementById("premiumBadge");
const statsFree = document.getElementById("statsFree");
const statsPremium = document.getElementById("statsPremium");
const statFocusTime = document.getElementById("statFocusTime");
const statSessions = document.getElementById("statSessions");
const optionsLink = document.getElementById("optionsLink");
const upgradeFromStats = document.getElementById("upgradeFromStats");

let countdownHandle = null;

function formatTime(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (totalSeconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function renderTimer(state) {
  const { timer } = state;
  modeLabel.textContent = timer.mode === "break" ? "휴식 시간" : "집중 세션";

  let remainingMs;
  if (timer.running && timer.endsAt) {
    remainingMs = timer.endsAt - Date.now();
  } else if (timer.remainingMs != null) {
    remainingMs = timer.remainingMs;
  } else {
    const minutes = timer.mode === "break" ? timer.breakMinutes : timer.focusMinutes;
    remainingMs = minutes * 60 * 1000;
  }
  timeDisplay.textContent = formatTime(remainingMs);

  startBtn.hidden = timer.running || timer.remainingMs != null;
  pauseBtn.hidden = !timer.running;
  resumeBtn.hidden = timer.running || timer.remainingMs == null;
  resetBtn.hidden = !timer.running && timer.remainingMs == null;
}

async function refresh() {
  const [state, premium] = await Promise.all([getAll(), isPremium()]);
  renderTimer(state);

  premiumBadge.hidden = !premium;
  groupByDomainBtn.textContent = premium ? "도메인별 그룹핑" : "도메인별 그룹핑 🔒";

  if (premium) {
    statsFree.hidden = true;
    statsPremium.hidden = false;
    statFocusTime.textContent = `${Math.round(state.stats.focusSecondsToday / 60)}분`;
    statSessions.textContent = String(state.stats.sessionsCompleted);
  } else {
    statsFree.hidden = false;
    statsPremium.hidden = true;
  }
}

async function refreshTabCount() {
  const tabs = await chrome.tabs.query({});
  tabCountLabel.textContent = `현재 열려 있는 탭: ${tabs.length}개`;
}

function startCountdownLoop() {
  if (countdownHandle) clearInterval(countdownHandle);
  countdownHandle = setInterval(refresh, 1000);
}

startBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "timer:start", mode: "focus" });
  refresh();
});

startBreakBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "timer:start", mode: "break" });
  refresh();
});

pauseBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "timer:pause" });
  refresh();
});

resumeBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "timer:resume" });
  refresh();
});

resetBtn.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "timer:reset" });
  refresh();
});

closeDuplicatesBtn.addEventListener("click", async () => {
  const res = await chrome.runtime.sendMessage({ type: "tabs:closeDuplicates" });
  tabCountLabel.textContent = `중복 탭 ${res.closed}개를 닫았습니다.`;
  setTimeout(refreshTabCount, 1500);
});

groupByDomainBtn.addEventListener("click", async () => {
  const premium = await isPremium();
  if (!premium) {
    chrome.runtime.openOptionsPage();
    return;
  }
  const res = await chrome.runtime.sendMessage({ type: "tabs:groupByDomain" });
  if (res.ok) {
    tabCountLabel.textContent = `${res.groups}개의 도메인 그룹을 만들었습니다.`;
  }
});

optionsLink.addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

upgradeFromStats.addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

refresh();
refreshTabCount();
startCountdownLoop();
