# lesson4
# Sample-repository
This is a sample repository.
We have edited the README file. 
##

## Site Launch Pipeline

Every new site goes through the same 6 steps:

1. 사이트 개발 (site development)
2. 도메인 구매 (domain purchase)
3. 배포 환경에 도메인 연결 (connect domain to hosting)
4. 구글 서치콘솔 · 네이버 서치어드바이저 등록
5. 다음 검색 · Bing 웹마스터 도구 등록
6. 애드센스 승인 신청

`.github/workflows/site-launch-pipeline.yml` automates this checklist:

- Run it manually (Actions tab → "Site Launch Pipeline" → Run workflow) with the site name, domain, and optional sitemap URL.
- It pings Google's sitemap endpoint and submits to IndexNow (covers Bing, Naver, Yandex, Seznam) via `scripts/ping-search-engines.sh`. Set an `INDEXNOW_KEY` repository secret to enable the IndexNow submission (requires hosting `https://<domain>/<key>.txt` with that key).
- It opens a tracking issue with a checklist for the whole process, pre-checking the steps the pipeline just automated and leaving domain purchase, DNS connection, and AdSense application for manual follow-up.
