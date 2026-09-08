# lesson4

# 드롭쉬핑 AI 에이전트

Claude API(Opus 5)와 도구 호출(tool use)을 이용해 1인 드롭쉬핑 셀러의 반복 업무를
자동화하는 데모 에이전트입니다. 이번 달 목표 매출은 **100만원**으로 설정되어 있고,
에이전트는 실제 매출 데이터를 기준으로 목표 달성 페이스를 계산해줍니다.

## 주요 기능

에이전트는 대화 중 필요에 따라 아래 도구를 스스로 호출합니다.

| 기능 | 도구 | 설명 |
|---|---|---|
| 상품 리서치/소싱 | `search_products` | 키워드로 트렌드 상품 후보와 공급업체 정보를 검색 |
| 가격 책정 | `calculate_pricing` | 공급가+배송비+수수료를 반영해 목표 마진율 기준 판매가 계산, 목표 매출 달성에 필요한 판매 수량까지 안내 |
| 재고/가격 모니터링 | `check_inventory_and_price` | 공급가 인상, 재고 부족 여부를 점검하고 경고 |
| 주문 처리 자동화 | `process_order` | 신규 주문을 공급업체로 발주 처리, 발주번호/예상 배송일 생성 |
| 고객 응대 챗봇 | `lookup_order_status` | 고객 문의에 응답할 주문/배송 상태 조회 |
| 매출 리포트 | `get_sales_summary` | 이번 달 누적 매출, 목표(100만원) 대비 달성률, 필요한 일 매출 페이스 계산 |

상품/주문 데이터는 `dropshipping_agent/data/*.json`의 모의(mock) 데이터를 사용하며,
실제 서비스로 확장할 때는 `store.py`를 실제 DB나 공급업체 API 연동으로 교체하면 됩니다.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # .env 파일에 ANTHROPIC_API_KEY 입력
```

## 실행

```bash
# 대화형 모드
python -m dropshipping_agent.cli

# 미리 정의된 질문으로 전체 기능을 한 번에 시연하는 데모 모드
python -m dropshipping_agent.cli --demo
```

## 테스트

API 키 없이 가격 계산, 재고 점검, 주문 처리 등 핵심 로직만 검증하는 오프라인 테스트:

```bash
python -m tests.test_tools
```

## 구조

```
dropshipping_agent/
  config.py    # 모델, 수수료율, 목표 매출 등 설정값
  store.py     # 모의 상품/주문 데이터 접근 계층
  tools.py     # 도구 정의(JSON 스키마) + 실제 구현 로직
  agent.py     # Claude 도구 호출 루프를 직접 관리하는 에이전트
  cli.py       # 대화형/데모 CLI 진입점
  data/        # 모의 상품 카탈로그, 주문 데이터 (JSON)
tests/
  test_tools.py  # 오프라인(비-API) 로직 테스트
```

