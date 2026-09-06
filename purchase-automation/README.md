# 구매 리스트 자동화 파이프라인 (Zentrada 대안 소싱)

Zentrada 외에 다른 소싱 플랫폼에서도 동일한 방식으로 "구매 리스트 추천"을 자동화하기 위한 파이프라인입니다.

## 왜 오너클랜(OwnerClan)인가

판매 채널이 **자사몰(Shopify) + 오픈마켓(쿠팡/네이버/이베이)** 이라는 전제 하에, Zentrada(유럽 B2B 도매/재고정리)의 대안으로는 국내 오픈마켓과 바로 연결되는 국내 B2B 도매 플랫폼이 유리합니다.

| 플랫폼 | 특징 | API |
|---|---|---|
| **오너클랜 (1순위)** | 국내 최대급 위탁도매, 카테고리 무관, 통관/배송 이슈 없음 | 공식 Open API (OAuth2 + GraphQL) |
| 도매매 (대안) | 카테고리 다양, 오너클랜과 병행 소싱 가능 | Open API 제공 |
| CJdropshipping (해외 병행 시) | 이베이 등 해외 채널 대응에 유리 | REST API |

이 저장소는 **오너클랜 커넥터**를 우선 구현했고, 다른 플랫폼은 `src/purchase_pipeline/platforms/base.py`의 `SourcingPlatform` 인터페이스만 구현하면 동일한 파이프라인에 바로 연결됩니다.

## 아키텍처

```
[오너클랜 API] --fetch_catalog()--> [Product 목록]
                                          |
                                          v
                              [scoring.py: 채널별 수수료 반영
                               마진율 + 수요점수로 필터링/랭킹]
                                          |
                                          v
                         +----------------+----------------+
                         |                |                |
                   [CSV 저장]      [Shopify 임시상품 등록]  [쿠팡/네이버/이베이
                    (감사용)         (draft product)         벌크업로드 CSV]
                         |
                         v
                  [Slack 알림 (선택)]
```

GitHub Actions가 매일 정해진 시각에 위 파이프라인 전체를 실행합니다(`.github/workflows/purchase_pipeline.yml`).

## 디렉터리 구조

```
purchase-automation/
  config.example.yaml          # 설정 템플릿 (복사해서 config.yaml로 사용)
  requirements.txt
  src/purchase_pipeline/
    models.py                  # Product / ChannelFee / PurchaseListItem
    config.py                  # YAML 설정 로더
    scoring.py                 # 마진율+수요점수 기반 필터링/랭킹
    pipeline.py                # CLI 진입점 (fetch -> score -> export -> notify)
    notify.py                  # Slack 알림 (선택)
    platforms/
      base.py                  # 새 플랫폼 추가 시 구현할 인터페이스
      ownerclan.py              # 오너클랜 커넥터 (mock 모드 지원)
    exporters/
      csv_exporter.py           # 전체 추천 리스트 CSV
      marketplace_exporter.py   # 쿠팡/네이버/이베이 벌크업로드용 CSV
      shopify_exporter.py       # Shopify 임시상품(draft) 등록
  tests/
    fixtures/ownerclan_sample.json
    test_scoring.py
    test_ownerclan_platform.py
```

## 로컬 실행

```bash
cd purchase-automation
pip install -r requirements.txt
cp config.example.yaml config.yaml   # 필요시 임계값/수수료 조정

# 자격 증명 없이 실행하면 오너클랜 커넥터가 자동으로 mock 모드(fixture 데이터)로 동작합니다.
PYTHONPATH=src python -m purchase_pipeline.pipeline --config config.yaml --dry-run

# 테스트
PYTHONPATH=src python -m pytest -q
```

실행 결과는 `output/purchase_list_YYYY-MM-DD.csv`(전체 추천 리스트)와 `output/{coupang,naver,ebay}_YYYY-MM-DD.csv`(채널별 벌크업로드용)로 생성됩니다.

## 실제 API 연동하기

환경 변수(로컬 `.env` 또는 GitHub Actions Secrets)로 자격 증명을 넣으면 mock 모드에서 실제 API 호출로 자동 전환됩니다.

| 변수 | 용도 |
|---|---|
| `OWNERCLAN_CLIENT_ID` / `OWNERCLAN_CLIENT_SECRET` | 오너클랜 Open API OAuth2 클라이언트 자격 증명 (판매자센터에서 발급) |
| `SHOPIFY_SHOP` / `SHOPIFY_ACCESS_TOKEN` | Shopify Admin API 커스텀 앱 토큰 (`write_products` 권한) |
| `SLACK_WEBHOOK_URL` | 실행 결과 요약을 받을 Slack Incoming Webhook (선택) |

> 오너클랜 GraphQL 스키마 필드명은 공식 Open API 문서 기준으로 작성했습니다. 오너클랜 쪽 스키마가 변경되면 `src/purchase_pipeline/platforms/ownerclan.py`의 `_CATALOG_QUERY`와 `_to_product()`만 맞춰 수정하면 됩니다.

쿠팡(Wing)/네이버(커머스 API)는 셀러별 카테고리 매핑과 API 승인이 필요해 우선 벌크업로드 CSV 형태로 산출하도록 했습니다. API 승인을 받으면 `marketplace_exporter.py`가 만드는 컬럼을 그대로 API 페이로드에 매핑하면 됩니다.

## 새 플랫폼(도매매 등) 추가하기

1. `src/purchase_pipeline/platforms/domeggook.py`를 만들고 `SourcingPlatform`(`fetch_catalog() -> list[Product]`)을 구현합니다.
2. `src/purchase_pipeline/platforms/__init__.py`의 `_REGISTRY`에 등록합니다.
3. `config.yaml`의 `platform:` 값을 바꾸면 나머지 스코어링/익스포트/알림 로직은 그대로 재사용됩니다.

## 자동 실행 스케줄

`.github/workflows/purchase_pipeline.yml`이 매일 00:00 UTC(09:00 KST)에 파이프라인을 실행하고 결과를 워크플로 아티팩트로 업로드합니다. 저장소 Settings → Secrets and variables → Actions에 위 표의 자격 증명을 등록하면 실제 데이터로 자동 실행됩니다(등록 전까지는 mock 데이터로 안전하게 동작합니다).
