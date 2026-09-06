# 구매 리스트 자동화 파이프라인 (Zentrada 대안 소싱)

Zentrada 외에 다른 소싱 플랫폼에서도 동일한 방식으로 "구매 리스트 추천"을 자동화하기 위한 파이프라인입니다. 판매 시장에 따라 소싱 플랫폼을 분리해 **두 개의 프로필**로 병행 운영합니다.

| 프로필 | 판매 시장 / 채널 | 소싱 플랫폼 | 월 비용 | 통화 |
|---|---|---|---|---|
| `config.ownerclan.example.yaml` | 한국: 자사몰(Shopify) + 쿠팡/네이버/이베이 | 오너클랜 | 가입비 무료 (거래 기반) | KRW |
| `config.syncee.example.yaml` (기본, 최대한 무료 지향) | 네덜란드/EU: 이미 Shopify에 있는 상품 중 Amazon.nl/Amazon.de에도 올릴 것 선별 | Syncee (Shopify 스토어 자체를 읽음) | **파이프라인 추가 비용 0원** (Shopify+Syncee 요금은 어차피 필요) | EUR |
| `config.dropxl.example.yaml` (대안) | 네덜란드/EU: 자사몰(Shopify) + Amazon.nl/Amazon.de | dropXL (vidaXL) | €30/월 | EUR |
| `config.bigbuy.example.yaml` (대안) | 〃 | BigBuy | €69~99/월 + 가입비 €45~90 | EUR |

## 왜 이 플랫폼인가

**오너클랜** — 판매 채널이 쿠팡/네이버 같은 국내 오픈마켓일 때는 Zentrada(유럽 B2B)보다 국내 위탁도매 플랫폼이 통관·배송·상품데이터(한글) 측면에서 유리합니다. 국내 최대급, 카테고리 무관, 공식 Open API(OAuth2 + GraphQL) 제공.

**BigBuy → dropXL → Syncee, 비용 문제로 단계적으로 교체함**

| 플랫폼 | 비용 | 비고 |
|---|---|---|
| BigBuy | €69~99/월 + 가입비 €45~90 | 카테고리 무관(전자기기 등)은 좋지만 비용이 가장 높음 |
| dropXL | 월 30유로, 판매 수수료 없음 | 네덜란드 자체 기업(vidaXL) → NL 배송 최快, API/CSV·XML 피드. 카테고리는 홈/가든/스포츠 등으로 제한적 |
| **Syncee (현재 기본값 — 최대한 무료)** | **파이프라인 입장에서 추가 비용 0원** | Syncee 자체는 무료~월 $19+ 플랜이 있지만, 애초에 **서버가 호출할 REST API가 없는** Shopify/WooCommerce 앱입니다 — 상품을 스토어에 직접 동기화하는 방식. 그래서 이 프로필은 Syncee API를 호출하는 대신, **Syncee가 이미 채워 넣은 내 Shopify 스토어 카탈로그를 그대로 읽어서**(원가 = Shopify의 "Cost per item" 필드) 그중 Amazon.nl/de에도 올릴 가치가 있는 상품을 골라줍니다. Shopify 계정은 어차피 있어야 하므로 이 파이프라인이 추가로 요구하는 비용/API는 없습니다. |

세 가지 다 코드로 구현되어 있으니, 카테고리 무관이 꼭 필요하면 BigBuy, 전용 API/피드가 필요하면 dropXL, 비용을 최우선하면 기본값인 Syncee 프로필을 쓰면 됩니다. 셋 다 `config: config.<이름>.example.yaml`만 바꾸면 전환됩니다.

이 저장소는 **오너클랜 · BigBuy · dropXL · Syncee(Shopify 카탈로그 읽기)** 네 커넥터를 구현했고, 다른 플랫폼은 `src/purchase_pipeline/platforms/base.py`의 `SourcingPlatform` 인터페이스만 구현하면 동일한 파이프라인에 바로 연결됩니다.

## 아키텍처

```
[소싱 플랫폼]   오너클랜(KR, GraphQL) / Syncee(NL, 내 Shopify 카탈로그 읽기)
                / dropXL(NL, CSV·XML 피드) / BigBuy(EU, REST) 등
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
 (감사용)      (draft product,           쿠팡/네이버/이베이/Amazon.nl/Amazon.de]
               Syncee 프로필에선 미사용)
 |
 v
[Slack 알림 (선택)]
```

GitHub Actions가 매일 정해진 시각에 **한국(오너클랜)과 네덜란드/EU(Syncee) 두 프로필을 매트릭스로 병렬 실행**합니다(`.github/workflows/purchase_pipeline.yml`).

## 디렉터리 구조

```
purchase-automation/
  config.ownerclan.example.yaml   # 한국 프로필 템플릿
  config.syncee.example.yaml      # 네덜란드/EU 프로필 템플릿 (기본, 최대한 무료)
  config.dropxl.example.yaml      # 네덜란드/EU 프로필 템플릿 (대안, 월 30유로 + 전용 피드)
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
      syncee.py                 # "Syncee" 커넥터 = 실제로는 내 Shopify 카탈로그를 읽음 (mock 모드 지원)
    exporters/
      csv_exporter.py           # 전체 추천 리스트 CSV
      marketplace_exporter.py   # 오픈마켓 벌크업로드용 CSV (쿠팡/네이버/이베이/Amazon.nl/Amazon.de)
      shopify_exporter.py       # Shopify 임시상품(draft) 등록
  tests/
    fixtures/{ownerclan,bigbuy}_sample.json, dropxl_sample.csv, syncee_shopify_sample.json
    test_scoring.py
    test_ownerclan_platform.py
    test_bigbuy_platform.py
    test_dropxl_platform.py
    test_syncee_platform.py
```

## 로컬 실행

```bash
cd purchase-automation
pip install -r requirements.txt

# 한국(오너클랜) 프로필
cp config.ownerclan.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(Syncee, 기본 - 최대한 무료) 프로필
cp config.syncee.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(dropXL, 전용 API/피드가 필요할 때 대안) 프로필
cp config.dropxl.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(BigBuy, 카테고리 무관이 필요할 때 대안) 프로필
cp config.bigbuy.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 테스트
PYTHONPATH=src python -m pytest -q
```

자격 증명 없이 실행하면 해당 플랫폼 커넥터가 자동으로 mock 모드(fixture 데이터)로 동작합니다.

실행 결과는 각 프로필의 `output_dir`(오너클랜: `output/`, Syncee: `output/syncee/`, dropXL: `output/dropxl/`, BigBuy: `output/bigbuy/`) 아래에 `purchase_list_YYYY-MM-DD.csv`(전체 추천 리스트)와 채널별 벌크업로드 CSV(`{coupang,naver,ebay,amazon_nl,amazon_de}_YYYY-MM-DD.csv`)로 생성됩니다.

## 실제 API 연동하기

환경 변수(로컬 `.env` 또는 GitHub Actions Secrets)로 자격 증명을 넣으면 mock 모드에서 실제 API 호출로 자동 전환됩니다. **Shopify는 시장별로 다른 스토어를 쓸 가능성이 높아 KR/NL 접미사로 구분**합니다. Syncee 프로필은 아래 SHOPIFY_SHOP_NL/SHOPIFY_ACCESS_TOKEN_NL만 있으면 되고 별도 자격 증명이 필요 없습니다 (Syncee 자체 API가 없기 때문).

| 변수 | 용도 |
|---|---|
| `OWNERCLAN_CLIENT_ID` / `OWNERCLAN_CLIENT_SECRET` | 오너클랜 Open API OAuth2 클라이언트 자격 증명 (판매자센터에서 발급) |
| `SHOPIFY_SHOP_NL` / `SHOPIFY_ACCESS_TOKEN_NL` | 네덜란드向 Shopify 스토어 Admin API 커스텀 앱 토큰 (`read_products`, `read_inventory` 권한 — Syncee 프로필이 카탈로그를 읽는 데 사용) |
| `SHOPIFY_SHOP_KR` / `SHOPIFY_ACCESS_TOKEN_KR` | 한국向 Shopify 스토어 Admin API 커스텀 앱 토큰 (`write_products` 권한) |
| `DROPXL_FEED_URL` | dropXL 계정 설정에서 발급받는 상품 피드 URL (CSV/XML) — dropxl 프로필을 쓸 때만 필요 |
| `DROPXL_API_KEY` | dropXL API 키 (선택) — dropxl 프로필을 쓸 때만 필요 |
| `BIGBUY_API_KEY` | BigBuy REST API 키 (판매자 패널에서 발급) — bigbuy 프로필을 쓸 때만 필요 |
| `SLACK_WEBHOOK_URL` | 실행 결과 요약을 받을 Slack Incoming Webhook (선택, 모든 프로필 공용) |

로컬 실행 시에는 프로필에 맞는 `SHOPIFY_SHOP` / `SHOPIFY_ACCESS_TOKEN` 값을(위 KR/NL 값 중 해당하는 것으로) 직접 export 하면 됩니다. GitHub Actions에서는 워크플로가 매트릭스별로 알맞은 시크릿을 자동 매핑합니다.

> **검증 상태 (정확히 구분해서 적습니다)**
>
> - **Syncee**: Syncee가 실제로 존재하는 회사이자 Shopify/WooCommerce 등 커머스 플랫폼용 "앱"으로 동작한다는 것, 그리고 **서버가 직접 호출할 수 있는 공개 REST API가 없다**는 것은 검색으로 확인했습니다 (공식 개발자 API 문서를 찾지 못했고, 있는 건 앱 설치·JSON/CSV 파일 가져오기 기능뿐). 그래서 이 프로필은 Syncee를 호출하는 척 코드를 짜지 않고, 대신 검증된 사실만으로 설계했습니다: Shopify Admin REST API의 상품/재고 조회와 `InventoryItem.cost`("Cost per item") 필드는 Shopify 자체의 공식 기능이라 훨씬 신뢰도가 높습니다. **다만 이 방식이 실제로 유효하려면 Syncee(또는 어떤 공급사 앱이든)가 상품을 Shopify에 동기화할 때 "Cost per item" 필드까지 채워 넣어야 합니다** — 안 채워지면 그 상품은 원가를 알 수 없어 자동으로 스킵됩니다(`platforms/syncee.py`의 `_build_products` 참고). 실제 스토어에서 한 번 확인해보세요.
> - **dropXL**: vidaXL은 약 20년 된 네덜란드 벤로 소재 실존 기업(매출 4억 달러+)이고, 드랍쉬핑 프로그램이 2025년 10월 "dropshippingXL"에서 "dropXL"로 리브랜딩됐다는 것까지는 공개 기사로 확인했습니다. 월 30유로 요금제, CSV/XML 피드 제공도 여러 소스에서 일치합니다. **다만 실제 피드 URL의 정확한 컬럼명은 계정별로 발급되는 것이라 공개 문서로 확인할 방법이 없었습니다** — 그래서 `platforms/dropxl.py`는 컬럼명을 하드코딩하지 않고 `column_map`으로 설정에서 조정하도록 만들었습니다.
> - **BigBuy**: 회사(2012년 스페인 발렌시아 설립)와 "API를 BigBuy 본사가 자사 도메인에서 직접 제공한다"는 사실은 1차 출처로 확인했습니다. 하지만 코드 속 엔드포인트 경로·필드명은 이 세션에서 bigbuy.eu 접속이 막혀 있어 서드파티 연동 코드를 참고해 작성한 것이라, 실제 API 키로 한 번 확인이 필요합니다.
> - **오너클랜**: GraphQL 스키마 필드명은 공식 Open API 문서 기준으로 작성했으나, 마찬가지로 실제 자격증명으로 첫 호출 시 응답 구조를 재확인하는 것을 권장합니다.
>
> 공통 원칙: 스키마가 다르면 해당 플랫폼 모듈의 쿼리/파싱 함수만 맞춰 수정하면 나머지 파이프라인(스코어링/익스포트/알림)은 그대로 재사용됩니다.

오픈마켓 API(쿠팡 Wing, 네이버 커머스, Amazon SP-API)는 셀러별 카테고리 매핑과 사전 승인이 필요해 우선 벌크업로드 CSV 형태로 산출하도록 했습니다. API 승인을 받으면 `marketplace_exporter.py`가 만드는 컬럼을 그대로 API 페이로드에 매핑하면 됩니다.

## 새 플랫폼(도매매 등) 추가하기

1. `src/purchase_pipeline/platforms/<name>.py`를 만들고 `SourcingPlatform`(`fetch_catalog() -> list[Product]`)을 구현합니다.
2. `src/purchase_pipeline/platforms/__init__.py`의 `_REGISTRY`에 등록합니다.
3. `config.<name>.example.yaml`을 하나 추가해 `platform:` 값과 채널/수수료를 설정하면 스코어링/익스포트/알림 로직은 그대로 재사용됩니다.

## 자동 실행 스케줄

`.github/workflows/purchase_pipeline.yml`이 매일 00:00 UTC(09:00 KST)에 **오너클랜(KR)과 Syncee(NL/EU, 최대한 무료) 두 프로필을 매트릭스로 병렬 실행**하고, 결과를 프로필별 워크플로 아티팩트로 업로드합니다. 저장소 Settings → Secrets and variables → Actions에 위 표의 자격 증명을 등록하면 실제 데이터로 자동 실행됩니다(등록 전까지는 mock 데이터로 안전하게 동작합니다). dropXL이나 BigBuy 프로필로 되돌리려면 워크플로의 매트릭스 항목을 해당 `config.*.example.yaml`로 바꾸면 됩니다.
