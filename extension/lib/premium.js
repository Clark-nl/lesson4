// 프리미엄 라이선스 검증.
//
// 기본 구현은 Gumroad의 공개 License Verification API를 사용합니다.
// (https://api.gumroad.com/v2/licenses/verify — Gumroad 문서에 공개된 표준 엔드포인트)
// 다른 결제 플랫폼(Lemon Squeezy, Paddle 등)을 쓸 경우 verifyLicenseKey만 교체하면 됩니다.
//
// 배포 전 GUMROAD_PRODUCT_PERMALINK를 본인 상품의 permalink로 바꾸세요.
const GUMROAD_PRODUCT_PERMALINK = "YOUR_GUMROAD_PRODUCT_PERMALINK";
const GUMROAD_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify";

import { getPremiumFlag, setPremiumFlag } from "./storage.js";

/**
 * Gumroad에 라이선스 키를 검증 요청합니다.
 * @param {string} licenseKey
 * @returns {Promise<{ok: boolean, message: string}>}
 */
async function verifyLicenseKey(licenseKey) {
  const trimmed = (licenseKey || "").trim();
  if (!trimmed) {
    return { ok: false, message: "라이선스 키를 입력해주세요." };
  }

  try {
    const body = new URLSearchParams({
      product_permalink: GUMROAD_PRODUCT_PERMALINK,
      license_key: trimmed,
    });
    const res = await fetch(GUMROAD_VERIFY_URL, { method: "POST", body });
    const data = await res.json();

    if (data.success && data.purchase && !data.purchase.refunded && !data.purchase.chargebacked) {
      await setPremiumFlag(true);
      await chrome.storage.sync.set({ licenseKey: trimmed });
      return { ok: true, message: "프리미엄이 활성화되었습니다. 감사합니다!" };
    }
    return { ok: false, message: "유효하지 않거나 환불된 라이선스 키입니다." };
  } catch (err) {
    return { ok: false, message: "검증 서버에 연결하지 못했습니다. 인터넷 연결을 확인해주세요." };
  }
}

async function isPremium() {
  return getPremiumFlag();
}

async function deactivatePremium() {
  await setPremiumFlag(false);
  await chrome.storage.sync.remove(["licenseKey"]);
}

export { verifyLicenseKey, isPremium, deactivatePremium, GUMROAD_PRODUCT_PERMALINK };
