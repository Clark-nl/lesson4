# Focus & Tabs

중복 탭 정리 + 뽀모도로 포커스 타이머를 제공하는 크롬 익스텐션(Manifest V3). 프리미엄 라이선스로 커스텀 타이머 길이, 도메인별 탭 자동 그룹핑, 유휴 탭 자동 정리, 집중 통계를 잠금 해제합니다.

## 무료 / 프리미엄 기능

| 기능 | 무료 | 프리미엄 |
|---|---|---|
| 뽀모도로 타이머 (25/5분 고정) | ✅ | ✅ |
| 커스텀 타이머 길이 | ❌ | ✅ |
| 중복 탭 닫기 | ✅ | ✅ |
| 도메인별 탭 자동 그룹핑 | ❌ | ✅ |
| 유휴 탭 자동 정리 | ❌ | ✅ |
| 오늘의 집중 통계 (시간/세션 수) | ❌ | ✅ |

## 로컬에서 실행하기 (개발용)

1. Chrome에서 `chrome://extensions` 접속
2. 우측 상단 "개발자 모드" 켜기
3. "압축해제된 확장 프로그램을 로드합니다" 클릭 → 이 `extension/` 폴더 선택
4. 툴바에서 아이콘 클릭해 팝업 확인

코드 수정 후에는 `chrome://extensions`에서 새로고침(⟳) 버튼으로 반영합니다.

## 프리미엄 라이선스 연동 (Gumroad)

기본값은 [Gumroad License Verification API](https://api.gumroad.com/v2/licenses/verify)를 사용합니다.

1. Gumroad에서 상품을 만들고 "Generate a unique license key per sale" 옵션을 켭니다.
2. `lib/premium.js`의 `GUMROAD_PRODUCT_PERMALINK` 값을 본인 상품의 permalink로 교체합니다.
3. `options.html`의 `buyLink` href를 실제 구매 페이지 URL로 교체합니다.
4. 다른 결제 플랫폼(Lemon Squeezy, Paddle, 자체 서버)을 쓰려면 `verifyLicenseKey()` 함수만 교체하면 나머지 코드는 그대로 동작합니다.

## Chrome 웹스토어에 배포하기

1. `manifest.json`의 `name`, `description`을 다듬고 스크린샷/프로모 이미지를 준비합니다.
2. `extension/` 폴더를 zip으로 압축합니다 (폴더 자체가 아니라 안의 파일들을 압축).
3. [Chrome Web Store 개발자 대시보드](https://chrome.google.com/webstore/devconsole)에 등록비($5, 최초 1회)를 내고 zip을 업로드합니다.
4. 개인정보 처리방침(탭 URL을 어떻게 다루는지 명시) 페이지 링크를 등록합니다 — `tabs` 권한을 쓰므로 필수입니다.

## 폴더 구조

```
extension/
  manifest.json      MV3 매니페스트
  popup.html/css/js   팝업 UI (타이머, 탭 정리, 통계)
  options.html/css/js 설정 페이지 (라이선스 활성화, 커스텀 설정)
  background.js       서비스 워커 (타이머 알람, 탭 정리 로직)
  lib/storage.js       공용 storage 헬퍼
  lib/premium.js       라이선스 검증 / 프리미엄 상태 관리
  icons/                16/32/48/128px 아이콘
```

## 이 코드베이스를 판매용 템플릿으로 쓰려면

`../docs/SELLING_AS_TEMPLATE.md`에 다른 개발자에게 보일러플레이트로 판매하는 방법과 판매 페이지 카피 초안이 있습니다.
