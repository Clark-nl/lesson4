# lesson4
# Sample-repository
This is a sample repository.
We have edited the README file. 
##

## Zentrada 알림2: 구매예상 품목 알림

Zentrada(B2B 도매 플랫폼)에 로그인해 개인화 추천/베스트셀러 목록을 가져온 뒤,
관심 키워드에 매칭되는 "구매예상 품목"을 Gmail로 알려주는 스크립트입니다.

### 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env를 열어 계정 정보, Gmail 앱 비밀번호 등을 채워 넣습니다.
```

Gmail은 일반 로그인 비밀번호가 아니라 [앱 비밀번호](https://myaccount.google.com/apppasswords)를
`EMAIL_APP_PASSWORD`에 설정해야 합니다.

### 셀렉터 조정 (중요)

`.env`의 `SELECTOR_PRODUCT_*` 값들은 실제 Zentrada 추천 페이지 마크업을 확인하지 못한 상태의
예시값입니다. 로그인 후 추천/베스트셀러 페이지에서 브라우저 개발자 도구로 상품 카드 요소를
확인하고, `SELECTOR_PRODUCT_CARD` / `SELECTOR_PRODUCT_NAME` / `SELECTOR_PRODUCT_PRICE` /
`SELECTOR_PRODUCT_LINK`를 실제 CSS 선택자로 맞춰주세요. 로그인 폼의 필드명
(`LOGIN_FORM_USERNAME_FIELD`, `LOGIN_FORM_PASSWORD_FIELD`)도 마찬가지입니다.

### 실행

```bash
# 실제 사이트에 로그인해 알림 발송
python -m zentrada_alert.main

# 네트워크 접속 없이 샘플 HTML로 파싱/필터링만 검증 (이메일도 실제 발송됨)
python -m zentrada_alert.main --dry-run-fixture tests/fixtures/sample_recommendations.html
```

주기 실행이 필요하면 cron 등으로 위 명령을 예약하세요 (예: 매일 오전 9시).

### 테스트

```bash
pytest
```
