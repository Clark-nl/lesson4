import { getAll, set } from "./lib/storage.js";
import { verifyLicenseKey, isPremium, deactivatePremium } from "./lib/premium.js";

const premiumInactive = document.getElementById("premiumInactive");
const premiumActive = document.getElementById("premiumActive");
const licenseInput = document.getElementById("licenseInput");
const activateBtn = document.getElementById("activateBtn");
const deactivateBtn = document.getElementById("deactivateBtn");
const licenseMessage = document.getElementById("licenseMessage");

const focusMinutesInput = document.getElementById("focusMinutes");
const breakMinutesInput = document.getElementById("breakMinutes");
const timerLockNote = document.getElementById("timerLockNote");

const autoCleanupEnabled = document.getElementById("autoCleanupEnabled");
const idleMinutesInput = document.getElementById("idleMinutes");
const cleanupLockNote = document.getElementById("cleanupLockNote");

const saveBtn = document.getElementById("saveBtn");
const saveMessage = document.getElementById("saveMessage");

async function render() {
  const [state, premium] = await Promise.all([getAll(), isPremium()]);

  premiumInactive.hidden = premium;
  premiumActive.hidden = !premium;

  focusMinutesInput.value = state.timer.focusMinutes;
  breakMinutesInput.value = state.timer.breakMinutes;
  focusMinutesInput.disabled = !premium;
  breakMinutesInput.disabled = !premium;
  timerLockNote.hidden = premium;

  autoCleanupEnabled.checked = state.autoCleanup.enabled;
  idleMinutesInput.value = state.autoCleanup.idleMinutes;
  autoCleanupEnabled.disabled = !premium;
  idleMinutesInput.disabled = !premium;
  cleanupLockNote.hidden = premium;
}

activateBtn.addEventListener("click", async () => {
  licenseMessage.textContent = "확인 중...";
  const result = await verifyLicenseKey(licenseInput.value);
  licenseMessage.textContent = result.message;
  if (result.ok) {
    licenseInput.value = "";
    render();
  }
});

deactivateBtn.addEventListener("click", async () => {
  await deactivatePremium();
  render();
});

saveBtn.addEventListener("click", async () => {
  const state = await getAll();
  const premium = await isPremium();

  const patch = {
    timer: {
      ...state.timer,
      focusMinutes: premium
        ? clamp(Number(focusMinutesInput.value) || 25, 1, 180)
        : state.timer.focusMinutes,
      breakMinutes: premium
        ? clamp(Number(breakMinutesInput.value) || 5, 1, 60)
        : state.timer.breakMinutes,
    },
    autoCleanup: {
      enabled: premium ? autoCleanupEnabled.checked : false,
      idleMinutes: premium ? clamp(Number(idleMinutesInput.value) || 60, 10, 1440) : state.autoCleanup.idleMinutes,
    },
  };

  await set(patch);
  saveMessage.textContent = "저장되었습니다.";
  setTimeout(() => (saveMessage.textContent = ""), 2000);
  render();
});

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

render();
