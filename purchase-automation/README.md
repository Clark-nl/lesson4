# 구매 리스트 자동화 파이프라인 (Zentrada 대안 소싱)

Zentrada 외에 다른 소싱 플랫폼에서도 동일한 방식으로 "구매 리스트 추천"을 자동화하기 위한 파이프라인입니다. 판매 시장에 따라 소싱 플랫폼을 분리해 **두 개의 프로필**로 병행 운영합니다.

| 프로필 | 판매 시장 / 채널 | 소싱 플랫폼 | 월 비용 | 통화 |
|---|---|---|---|---|
| `config.ownerclan.example.yaml` | 한국: 자사몰(Shopify) + 쿠팡/네이버/이베이 | 오너클랜 | 가입비 무료 (거래 기반) | KRW |
| `config.dropxl.example.yaml` (기본) | 네덜란드/EU: 자사몰(Shopify) + Amazon.nl/Amazon.de | dropXL (vidaXL) | **€30/월** | EUR |
| `config.bigbuy.example.yaml` (대안) | 〃 | BigBuy | €69~99/월 + 가입비 €45~90 | EUR |

## 왜 이 플랫폼인가

**오너클랜** — 판매 채널이 쿠팡/네이버 같은 국내 오픈마켓일 때는 Zentrada(유럽 B2B)보다 국내 위탁도매 플랫폼이 통관·배송·상품데이터(한글) 측면에서 유리합니다. 국내 최대급, 카테고리 무관, 공식 Open API(OAuth2 + GraphQL) 제공.

**BigBuy → dropXL로 교체함 (비용 문제)** — 처음엔 BigBuy(EU 창고, 카테고리 무관)를 추천했지만, 실제로 확인해보니 **월 69~99유로 + 가입비 45~90유로 + 커넥터 추가비용**으로 비용이 높았습니다. 대안을 비교한 결과:

| 플랫폼 | 비용 | 비고 |
|---|---|---|
| **dropXL (현재 채택)** | **월 30유로**, 판매 수수료 없음 | 네덜란드 자체 기업(vidaXL) → NL 배송 최快. API/CSV·XML 피드로 지금 구조에 그대로 맞음. 카테고리는 홈/가든/스포츠/완구 등으로 제한적 |
| BigBuy (여전히 코드는 남겨둠) | €69~99/월 + 가입비 | 카테고리 무관(전자기기 등)이 꼭 필요하면 여전히 유효한 선택지 |
| Syncee (검토 후 제외) | 월 $19~40, 무료 플랜도 있음, 카테고리 무관 | 가장 저렴하지만 서버용 REST API가 없고 Shopify/WooCommerce **앱 설치 + CSV 가져오기** 방식이라 지금의 "서버가 API로 자동 수집" 구조와 안 맞아서 제외 |

즉 전자기기 등 카테고리 무관이 꼭 필요하면 `config.bigbuy.example.yaml`을 계속 쓰시면 되고, 비용을 우선하면 기본값인 dropXL을 쓰면 됩니다.

이 저장소는 **오너클랜 · BigBuy · dropXL** 세 커넥터를 구현했고, 다른 플랫폼은 `src/purchase_pipeline/platforms/base.py`의 `SourcingPlatform` 인터페이스만 구현하면 동일한 파이프라인에 바로 연결됩니다.

## 아키텍처

```
[소싱 플랫폼]   오너클랜(KR, GraphQL) / dropXL(NL, CSV·XML 피드) / BigBuy(EU, REST) 등
      |  fetch_catalog()          - platform: 설정값으로 전환
      v
 [Product 목록]
      |
      v
[scoring.py: 채널별 수수료 반영
 마진율(+수요점수, 데이터 있는 경우)로 필터링/랭킹]
      |
      v
 +----------------+------------------------+
 |                |                        |
[CSV 저장]   [Shopify 임시상품 등록]   [오픈마켓 벌크업로드 CSV
 (감사용)      (draft product)          쿠팡/네이버/이베이/Amazon.nl/Amazon.de]
 |
 v
[Slack 알림 (선택)]
```

GitHub Actions가 매일 정해진 시각에 **한국(오너클랜)과 네덜란드/EU(dropXL) 두 프로필을 매트릭스로 병렬 실행**합니다(`.github/workflows/purchase_pipeline.yml`).

## 디렉터리 구조

```
purchase-automation/
  config.ownerclan.example.yaml   # 한국 프로필 템플릿
  config.dropxl.example.yaml      # 네덜란드/EU 프로필 템플릿 (기본, 저비용)
  config.bigbuy.example.yaml      # 네덜란드/EU 프로필 템플릿 (대안, 카테고리 무관이 필요할 때)
  requirements.txt
  src/purchase_pipeline/
    models.py                  # Product / ChannelFee / PurchaseListItem
    config.py                  # YAML 설정 로더
    scoring.py                 # 마진율(+수요점수) 기반 필터링/랭킹
    pipeline.py                # CLI 진입점 (fetch -> score -> export -> notify)
    notify.py                  # Slack 알림 (선택)
    platforms/
      base.py                  # 새 플랫폼 추가 시 구현할 인터페이스
      ownerclan.py              # 오너클랜 커넥터 (mock 모드 지원)
      bigbuy.py                 # BigBuy 커넥터 (mock 모드 지원)
      dropxl.py                 # dropXL 커넥터 (CSV/XML 피드, 컬럼 매핑 설정 가능, mock 모드 지원)
    exporters/
      csv_exporter.py           # 전체 추천 리스트 CSV
      marketplace_exporter.py   # 오픈마켓 벌크업로드용 CSV (쿠팡/네이버/이베이/Amazon.nl/Amazon.de)
      shopify_exporter.py       # Shopify 임시상품(draft) 등록
  tests/
    fixtures/{ownerclan,bigbuy}_sample.json, dropxl_sample.csv
    test_scoring.py
    test_ownerclan_platform.py
    test_bigbuy_platform.py
    test_dropxl_platform.py
```

## 로컬 실행

```bash
cd purchase-automation
pip install -r requirements.txt

# 한국(오너클랜) 프로필
cp config.ownerclan.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(dropXL, 기본) 프로필
cp config.dropxl.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(BigBuy, 카테고리 무관이 필요할 때 대안) 프로필
cp config.bigbuy.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 테스트
PYTHONPATH=src python -m pytest -q
```

자격 증명 없이 실행하면 해당 플랫폼 커넥터가 자동으로 mock 모드(fixture 데이터)로 동작합니다.

실행 결과는 각 프로필의 `output_dir`(오너클랜: `output/`, dropXL: `output/dropxl/`, BigBuy: `output/bigbuy/`) 아래에 `purchase_list_YYYY-MM-DD.csv`(전체 추천 리스트)와 채널별 벌크업로드 CSV(`{coupang,naver,ebay,amazon_nl,amazon_de}_YYYY-MM-DD.csv`)로 생성됩니다.

## 실제 API 연동하기

환경 변수(로컬 `.env` 또는 GitHub Actions Secrets)로 자격 증명을 넣으면 mock 모드에서 실제 API 호출로 자동 전환됩니다. **Shopify는 시장별로 다른 스토어를 쓸 가능성이 높아 KR/NL 접미사로 구분**합니다.

| 변수 | 용도 |
|---|---|
| `OWNERCLAN_CLIENT_ID` / `OWNERCLAN_CLIENT_SECRET` | 오너클랜 Open API OAuth2 클라이언트 자격 증명 (판매자센터에서 발급) |
| `DROPXL_FEED_URL` | dropXL 계정 설정에서 발급받는 상품 피드 URL (CSV/XML) |
| `DROPXL_API_KEY` | dropXL API 키 (선택, 계정에 따라 필요할 수 있음) |
| `BIGBUY_API_KEY` | BigBuy REST API 키 (판매자 패널에서 발급) — bigbuy 프로필을 쓸 때만 필요 |
| `SHOPIFY_SHOP_KR` / `SHOPIFY_ACCESS_TOKEN_KR` | 한국向 Shopify 스토어 Admin API 커스텀 앱 토큰 (`write_products` 권한) |
| `SHOPIFY_SHOP_NL` / `SHOPIFY_ACCESS_TOKEN_NL` | 네덜란드向 Shopify 스토어 Admin API 커스텀 앱 토큰 |
| `SLACK_WEBHOOK_URL` | 실행 결과 요약을 받을 Slack Incoming Webhook (선택, 모든 프로필 공용) |

로컬 실행 시에는 프로필에 맞는 `SHOPIFY_SHOP` / `SHOPIFY_ACCESS_TOKEN` 값을(위 KR/NL 값 중 해당하는 것으로) 직접 export 하면 됩니다. GitHub Actions에서는 워크플로가 매트릭스별로 알맞은 시크릿을 자동 매핑합니다.

> **검증 상태 (정확히 구분해서 적습니다)**
>
> - **dropXL**: vidaXL은 2012년... 이 아니라 약 20년 된 네덜란드 벤로 소재 실존 기업(매출 4억 달러+)이고, 드랍쉬핑 프로그램이 2025년 10월 "dropshippingXL"에서 "dropXL"로 리브랜딩됐다는 것까지는 공개 기사(dodropshipping.com, bootstrappingecommerce.com 등)로 확인했습니다. 월 30유로 요금제, CSV/XML 피드(재고 매시간·가격 매일 갱신) 제공도 여러 소스에서 일치합니다. **다만 실제 피드 URL의 정확한 컬럼명은 계정별로 발급되는 것이라 공개 문서로 확인할 방법이 없었습니다** — 그래서 `platforms/dropxl.py`는 컬럼명을 하드코딩하지 않고 `column_map`으로 설정에서 조정하도록 만들었습니다. 실제 계정을 받으면 피드를 한 번 열어보고 헤더에 맞게 `DEFAULT_CSV_COLUMN_MAP`(또는 커넥터 생성 시 전달하는 `column_map`)을 고치세요.
> - **BigBuy**: 회사(2012년 스페인 발렌시아 설립, 창업자 Salvador Esteve/Victor P. Amarnani, 매출 1.1억 유로)와 "API를 BigBuy 본사가 자사 도메인에서 직접 제공한다"는 사실은 1차 출처로 확인했습니다. 하지만 코드 속 엔드포인트 경로·필드명은 이 세션에서 bigbuy.eu 접속이 막혀 있어 서드파티 연동 코드를 참고해 작성한 것이라, 실제 API 키로 한 번 확인이 필요합니다 (`platforms/bigbuy.py` 상단 주석 참고).
> - **오너클랜**: GraphQL 스키마 필드명은 공식 Open API 문서 기준으로 작성했으나, 마찬가지로 실제 자격증명으로 첫 호출 시 응답 구조를 재확인하는 것을 권장합니다.
>
> 공통 원칙: 스키마가 다르면 해당 플랫폼 모듈의 쿼리/파싱 함수만 맞춰 수정하면 나머지 파이프라인(스코어링/익스포트/알림)은 그대로 재사용됩니다.

오픈마켓 API(쿠팡 Wing, 네이버 커머스, Amazon SP-API)는 셀러별 카테고리 매핑과 사전 승인이 필요해 우선 벌크업로드 CSV 형태로 산출하도록 했습니다. API 승인을 받으면 `marketplace_exporter.py`가 만드는 컬럼을 그대로 API 페이로드에 매핑하면 됩니다.

## 새 플랫폼(도매매, Syncee 등) 추가하기

1. `src/purchase_pipeline/platforms/<name>.py`를 만들고 `SourcingPlatform`(`fetch_catalog() -> list[Product]`)을 구현합니다.
2. `src/purchase_pipeline/platforms/__init__.py`의 `_REGISTRY`에 등록합니다.
3. `config.<name>.example.yaml`을 하나 추가해 `platform:` 값과 채널/수수료를 설정하면 스코어링/익스포트/알림 로직은 그대로 재사용됩니다.

(Syncee는 서버용 REST API가 없고 Shopify 앱 설치 방식이라 이 파이프라인 구조에는 맞지 않아 구현하지 않았습니다 — 필요하면 Shopify 스토어 쪽에 앱으로 직접 설치하는 것이 맞는 방향입니다.)

## 자동 실행 스케줄

`.github/workflows/purchase_pipeline.yml`이 매일 00:00 UTC(09:00 KST)에 **오너클랜(KR)과 dropXL(NL/EU) 두 프로필을 매트릭스로 병렬 실행**하고, 결과를 프로필별 워크플로 아티팩트로 업로드합니다. 저장소 Settings → Secrets and variables → Actions에 위 표의 자격 증명을 등록하면 실제 데이터로 자동 실행됩니다(등록 전까지는 mock 데이터로 안전하게 동작합니다). BigBuy 프로필로 되돌리려면 워크플로의 매트릭스 항목을 `config.bigbuy.example.yaml`로 바꾸면 됩니다.
