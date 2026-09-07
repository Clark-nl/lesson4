# lesson4

## Shopify 연동 빌더

Shopify 스토어를 OAuth로 연동하고, 스토어의 상품 데이터를 불러와 상품을 선택한 뒤
정적 쇼핑몰 랜딩 페이지(HTML)를 자동 생성/다운로드할 수 있는 웹앱입니다.

### 주요 기능
- Shopify OAuth 설치 플로우 (HMAC 검증, state 기반 CSRF 방지)
- Admin GraphQL API로 스토어 정보 및 상품 목록 조회
- 상품을 골라 테마(Light/Dark/Mint)를 적용한 스토어 랜딩 페이지 생성
- 브라우저 미리보기 + 생성된 HTML 파일 다운로드

### 프로젝트 구조
```
src/
  server.js        # Express 서버, 라우팅
  shopifyAuth.js    # OAuth URL 생성, HMAC/토큰 교환
  shopifyClient.js  # Shopify Admin GraphQL API 클라이언트
  storeBuilder.js   # 선택 상품으로 정적 HTML 스토어 페이지 생성
  store.js          # 데모용 인메모리 세션 저장소
public/
  index.html, style.css, app.js  # 빌더 UI
```

### 준비물
1. [Shopify Partner 계정](https://partners.shopify.com/)에서 앱 생성 후 API key/secret 발급
2. 앱의 Allowed redirection URL에 `<HOST>/auth/callback` 등록
3. 로컬 개발 시 외부에서 접근 가능한 터널(ngrok 등)로 `HOST`를 설정 (Shopify는 OAuth 콜백에 공개 URL이 필요)

### 실행 방법
```bash
npm install
cp .env.example .env   # SHOPIFY_API_KEY, SHOPIFY_API_SECRET, HOST 등 채우기
npm start               # http://localhost:3000
```

### 사용 흐름
1. 브라우저에서 앱 접속 → `your-store.myshopify.com` 입력 후 "Shopify 연동하기"
2. Shopify 인가 화면에서 앱 설치 승인 → 콜백으로 리다이렉트되며 연동 완료
3. 스토어 상품 목록에서 랜딩 페이지에 넣을 상품 선택
4. 스토어 이름/태그라인/테마 입력 후 "선택한 상품으로 페이지 생성"
5. 미리보기 확인 후 HTML 파일 다운로드

> 세션 저장소는 학습/데모 목적의 인메모리 구현입니다. 운영 환경에서는 DB/Redis 등
> 영속 저장소로 교체하고, HTTPS 및 시크릿 관리를 강화해야 합니다.
##
