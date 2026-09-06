# 구매 리스트 자동화 파이프라인 (Zentrada 대안 소싱)

Zentrada 외에 다른 소싱 플랫폼에서도 동일한 방식으로 "구매 리스트 추천"을 자동화하기 위한 파이프라인입니다. 판매 시장에 따라 소싱 플랫폼을 분리해 **두 개의 프로필**로 병행 운영합니다.

| 프로필 | 판매 시장 / 채널 | 소싱 플랫폼 | 통화 |
|---|---|---|---|
| `config.ownerclan.example.yaml` | 한국: 자사몰(Shopify) + 쿠팡/네이버/이베이 | 오너클랜 | KRW |
| `config.bigbuy.example.yaml` | 네덜란드/EU: 자사몰(Shopify) + Amazon.nl/Amazon.de | BigBuy | EUR |

## 왜 이 플랫폼인가

**오너클랜** — 판매 채널이 쿠팡/네이버 같은 국내 오픈마켓일 때는 Zentrada(유럽 B2B)보다 국내 위탁도매 플랫폼이 통관·배송·상품데이터(한글) 측면에서 유리합니다. 국내 최대급, 카테고리 무관, 공식 Open API(OAuth2 + GraphQL) 제공. 대안: 도매매, 해외 채널 확장 시 CJdropshipping.

**BigBuy** — 네덜란드/EU 판매는 EU 역내 창고에서 발송되어 통관 이슈가 없어야 하므로, Zentrada와 마찬가지로 EU 기반 B2B 도매 플랫폼이 자연스러운 대안입니다. 카테고리 무관(전자기기/생활용품/펫 등), 공식 REST API 제공, Amazon.nl/Amazon.de·Shopify(EU) 연동에 적합합니다.

| 플랫폼 | 특징 | API |
|---|---|---|
| **BigBuy (EU/NL 1순위)** | EU 창고 발송, 카테고리 무관, REST API | REST (Bearer 토큰) |
| VidaXL (대안) | 네덜란드 본사, 홈/가든/스포츠 특화 (카테고리 제한적) | REST API |
| Ankorstore (대안) | 부티크/독립 리테일 특화 B2B 마켓플레이스 | REST API |

이 저장소는 **오너클랜**과 **BigBuy** 커넥터를 구현했고, 다른 플랫폼은 `src/purchase_pipeline/platforms/base.py`의 `SourcingPlatform` 인터페이스만 구현하면 동일한 파이프라인에 바로 연결됩니다.

## 아키텍처

```
[소싱 플랫폼 API]        오너클랜(KR) / BigBuy(NL·EU) 등 - platform: 설정값으로 전환
      |  fetch_catalog()
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

GitHub Actions가 매일 정해진 시각에 **두 프로필을 매트릭스로 병렬 실행**합니다(`.github/workflows/purchase_pipeline.yml`).

## 디렉터리 구조

```
purchase-automation/
  config.ownerclan.example.yaml   # 한국 프로필 템플릿
  config.bigbuy.example.yaml      # 네덜란드/EU 프로필 템플릿
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
    exporters/
      csv_exporter.py           # 전체 추천 리스트 CSV
      marketplace_exporter.py   # 오픈마켓 벌크업로드용 CSV (쿠팡/네이버/이베이/Amazon.nl/Amazon.de)
      shopify_exporter.py       # Shopify 임시상품(draft) 등록
  tests/
    fixtures/{ownerclan,bigbuy}_sample.json
    test_scoring.py
    test_ownerclan_platform.py
    test_bigbuy_platform.py
```

## 로컬 실행

```bash
cd purchase-automation
pip install -r requirements.txt

# 한국(오너클랜) 프로필
cp config.ownerclan.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 네덜란드/EU(BigBuy) 프로필
cp config.bigbuy.example.yaml config.yaml
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 테스트
PYTHONPATH=src python -m pytest -q
```

자격 증명 없이 실행하면 해당 플랫폼 커넥터가 자동으로 mock 모드(fixture 데이터)로 동작합니다.

실행 결과는 각 프로필의 `output_dir`(오너클랜: `output/`, BigBuy: `output/bigbuy/`) 아래에 `purchase_list_YYYY-MM-DD.csv`(전체 추천 리스트)와 채널별 벌크업로드 CSV(`{coupang,naver,ebay,amazon_nl,amazon_de}_YYYY-MM-DD.csv`)로 생성됩니다.

## 실제 API 연동하기

환경 변수(로컬 `.env` 또는 GitHub Actions Secrets)로 자격 증명을 넣으면 mock 모드에서 실제 API 호출로 자동 전환됩니다. **Shopify는 시장별로 다른 스토어를 쓸 가능성이 높아 KR/NL 접미사로 구분**합니다.

| 변수 | 용도 |
|---|---|
| `OWNERCLAN_CLIENT_ID` / `OWNERCLAN_CLIENT_SECRET` | 오너클랜 Open API OAuth2 클라이언트 자격 증명 (판매자센터에서 발급) |
| `BIGBUY_API_KEY` | BigBuy REST API 키 (판매자 패널에서 발급) |
| `SHOPIFY_SHOP_KR` / `SHOPIFY_ACCESS_TOKEN_KR` | 한국向 Shopify 스토어 Admin API 커스텀 앱 토큰 (`write_products` 권한) |
| `SHOPIFY_SHOP_NL` / `SHOPIFY_ACCESS_TOKEN_NL` | 네덜란드向 Shopify 스토어 Admin API 커스텀 앱 토큰 |
| `SLACK_WEBHOOK_URL` | 실행 결과 요약을 받을 Slack Incoming Webhook (선택, 두 프로필 공용) |

로컬 실행 시에는 프로필에 맞는 `SHOPIFY_SHOP` / `SHOPIFY_ACCESS_TOKEN` 값을(위 KR/NL 값 중 해당하는 것으로) 직접 export 하면 됩니다. GitHub Actions에서는 워크플로가 매트릭스별로 알맞은 시크릿을 자동 매핑합니다.

> **검증 상태 (정확히 구분)**
>
> - **1차 출처로 확인됨 (확실)**: BigBuy는 2012년 스페인 발렌시아에서 설립된 실존 도매/드랍쉬핑 기업입니다 (창업자 Salvador Esteve, Victor P. Amarnani / 몬카다 소재 창고 약 3만m² / SKU 약 30만개, 20+ 카테고리 / 2022년 매출 1억1000만 유로, 95% 유럽 수출) — 위키피디아·Valencia Plaza·Emprendedores 등 스페인 언론 보도로 확인. 또한 BigBuy가 자사 도메인(bigbuy.eu)에 개발자 API 소개 페이지와 공식 PDF 가이드를 직접 호스팅하고 있다는 것도 검색 결과로 확인 — 즉 **API를 BigBuy 본사가 직접 제공하는 것은 맞고, 서드파티가 만든 게 아닙니다.**
> - **미확인 (주의 필요)**: 이 세션은 네트워크 정책상 `bigbuy.eu` 도메인 자체를 접속할 수 없어서, 저나 누구도 실제로 그 공식 PDF 가이드나 라이브 API 응답을 직접 읽어보지 못했습니다. 코드 안의 구체적인 엔드포인트 경로(`products.json`, `productsstock.json`)·인증 헤더(`Authorization: Bearer`)·필드명(`wholesalePrice`, `retailPrice`, `stocks[0].quantity` 등)은 **그 공식 API를 구현했다고 주장하는 서드파티 연동 코드**에서 가져온 것이지, 공식 문서를 직접 대조한 게 아닙니다. 즉 "회사와 API 제공 주체"는 확실하지만 "코드에 박아넣은 세부 스펙"은 여전히 잘 만든 추정치 수준입니다.
>
> **결론**: 실제 사용 전 `BIGBUY_API_KEY` 발급받아서 `products.json` 한 번 호출해보고, 응답이 `_to_product()`가 기대하는 구조와 맞는지 반드시 확인하세요. 다르면 `platforms/bigbuy.py`의 `_to_product()`와 `_fetch_catalog_live()` 두 곳만 고치면 나머지 파이프라인은 그대로 동작합니다.
>
> 오너클랜 GraphQL 스키마 필드명은 공식 Open API 문서 기준으로 작성했으나 마찬가지로 실제 자격증명으로 첫 호출 시 응답 구조를 재확인하는 것을 권장합니다. 스키마가 다르면 해당 플랫폼 모듈의 쿼리/파싱 함수만 맞춰 수정하면 나머지 파이프라인은 그대로 재사용됩니다.

오픈마켓 API(쿠팡 Wing, 네이버 커머스, Amazon SP-API)는 셀러별 카테고리 매핑과 사전 승인이 필요해 우선 벌크업로드 CSV 형태로 산출하도록 했습니다. API 승인을 받으면 `marketplace_exporter.py`가 만드는 컬럼을 그대로 API 페이로드에 매핑하면 됩니다.

## 새 플랫폼(도매매, VidaXL 등) 추가하기

1. `src/purchase_pipeline/platforms/<name>.py`를 만들고 `SourcingPlatform`(`fetch_catalog() -> list[Product]`)을 구현합니다.
2. `src/purchase_pipeline/platforms/__init__.py`의 `_REGISTRY`에 등록합니다.
3. `config.<name>.example.yaml`을 하나 추가해 `platform:` 값과 채널/수수료를 설정하면 스코어링/익스포트/알림 로직은 그대로 재사용됩니다.

## 자동 실행 스케줄

`.github/workflows/purchase_pipeline.yml`이 매일 00:00 UTC(09:00 KST)에 **오너클랜(KR)과 BigBuy(NL/EU) 두 프로필을 매트릭스로 병렬 실행**하고, 결과를 프로필별 워크플로 아티팩트로 업로드합니다. 저장소 Settings → Secrets and variables → Actions에 위 표의 자격 증명을 등록하면 실제 데이터로 자동 실행됩니다(등록 전까지는 mock 데이터로 안전하게 동작합니다).
