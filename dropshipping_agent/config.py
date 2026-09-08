"""에이전트 전역 설정값."""

from pathlib import Path

# Claude 모델 설정
MODEL = "claude-opus-5"
MAX_TOKENS = 4096

# 데이터 경로
DATA_DIR = Path(__file__).parent / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"
ORDERS_PATH = DATA_DIR / "orders.json"

# 판매 수수료 가정치 (오픈마켓 판매 수수료 + PG 결제 수수료)
MARKETPLACE_FEE_PCT = 10.0
PAYMENT_FEE_PCT = 3.3

# 기본 목표 마진율 (사용자가 지정하지 않았을 때)
DEFAULT_TARGET_MARGIN_PCT = 35.0

# 사업 목표: 예상(목표) 월 매출
TARGET_MONTHLY_REVENUE_KRW = 1_000_000

# 재고 경고 임계값: 공급가가 기준가 대비 이 비율(%) 이상 오르면 가격 재조정 필요로 표시
PRICE_ALERT_THRESHOLD_PCT = 5.0
