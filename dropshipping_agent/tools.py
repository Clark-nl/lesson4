"""에이전트가 호출하는 도구(함수) 정의와 실제 구현.

각 함수는 순수 파이썬 로직만 사용하며(모의 데이터 기반), Claude는 이 도구들을
호출해 실제 계산/조회/상태 변경을 수행한다.
"""

import hashlib
import json
import math
from datetime import date, datetime, timedelta
from typing import Any

from . import config, gmail_tools, store

# ---------------------------------------------------------------------------
# 도구 구현
# ---------------------------------------------------------------------------


def search_products(keyword: str, max_results: int = 5) -> dict[str, Any]:
    """키워드로 소싱 후보 상품을 검색한다 (트렌드 점수 순 정렬)."""
    keyword_lower = keyword.strip().lower()
    matches = [
        p
        for p in store.load_catalog()
        if keyword_lower in p["name"].lower()
        or keyword_lower in p["category"].lower()
        or any(keyword_lower in kw.lower() for kw in p["keywords"])
    ]
    matches.sort(key=lambda p: p["trend_score"], reverse=True)
    results = [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "supplier": p["supplier"],
            "supplier_email": p["supplier_email"],
            "supplier_rating": p["supplier_rating"],
            "current_supplier_price_krw": p["current_supplier_price_krw"],
            "shipping_days": p["shipping_days"],
            "monthly_search_volume": p["monthly_search_volume"],
            "trend_score": p["trend_score"],
        }
        for p in matches[:max_results]
    ]
    return {"query": keyword, "count": len(results), "results": results}


def calculate_pricing(product_id: str, target_margin_pct: float | None = None) -> dict[str, Any]:
    """공급가 + 배송비 + 수수료를 반영해 목표 마진을 달성하는 판매가를 계산한다."""
    product = store.find_product(product_id)
    if product is None:
        return {"error": f"상품 ID '{product_id}'를 찾을 수 없습니다."}

    margin_pct = (
        config.DEFAULT_TARGET_MARGIN_PCT if target_margin_pct is None else target_margin_pct
    )
    fee_pct = config.MARKETPLACE_FEE_PCT + config.PAYMENT_FEE_PCT
    denom = 1 - (fee_pct / 100) - (margin_pct / 100)
    if denom <= 0:
        return {
            "error": (
                f"목표 마진율({margin_pct}%)과 수수료율({fee_pct}%)의 합이 100%를 넘어 "
                "가격을 계산할 수 없습니다. 목표 마진율을 낮춰주세요."
            )
        }

    cost = product["current_supplier_price_krw"] + product["shipping_cost_krw"]
    raw_price = cost / denom
    # 실제 오픈마켓에서 흔한 100원 단위 가격으로 반올림
    recommended_price = math.ceil(raw_price / 100) * 100

    profit_per_unit = recommended_price * (1 - fee_pct / 100) - cost
    units_needed_for_target = math.ceil(
        config.TARGET_MONTHLY_REVENUE_KRW / recommended_price
    )

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "supplier_price_krw": product["current_supplier_price_krw"],
        "shipping_cost_krw": product["shipping_cost_krw"],
        "target_margin_pct": margin_pct,
        "assumed_fee_pct": fee_pct,
        "recommended_selling_price_krw": recommended_price,
        "estimated_profit_per_unit_krw": round(profit_per_unit),
        "units_needed_to_hit_monthly_target": units_needed_for_target,
        "target_monthly_revenue_krw": config.TARGET_MONTHLY_REVENUE_KRW,
    }


def check_inventory_and_price(product_id: str) -> dict[str, Any]:
    """공급가 변동 및 재고 부족 여부를 점검한다."""
    product = store.find_product(product_id)
    if product is None:
        return {"error": f"상품 ID '{product_id}'를 찾을 수 없습니다."}

    baseline = product["baseline_supplier_price_krw"]
    current = product["current_supplier_price_krw"]
    change_pct = round((current - baseline) / baseline * 100, 2) if baseline else 0.0

    alerts = []
    if change_pct >= config.PRICE_ALERT_THRESHOLD_PCT:
        alerts.append(
            f"공급가가 기준가 대비 {change_pct}% 상승했습니다. 판매가 재조정을 검토하세요."
        )
    if product["stock"] <= product["reorder_threshold"]:
        alerts.append(
            f"재고가 {product['stock']}개로 재주문 기준({product['reorder_threshold']}개) 이하입니다."
        )

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "baseline_supplier_price_krw": baseline,
        "current_supplier_price_krw": current,
        "price_change_pct": change_pct,
        "stock": product["stock"],
        "reorder_threshold": product["reorder_threshold"],
        "needs_attention": bool(alerts),
        "alerts": alerts,
    }


def process_order(order_id: str) -> dict[str, Any]:
    """신규 주문을 공급업체로 발주 처리하고 예상 배송 완료일을 계산한다."""
    orders = store.load_orders()
    order = next((o for o in orders if o["order_id"] == order_id), None)
    if order is None:
        return {"error": f"주문 ID '{order_id}'를 찾을 수 없습니다."}

    if order["status"] != "new":
        return {
            "order_id": order_id,
            "status": order["status"],
            "message": "이미 처리된 주문입니다 (신규 상태가 아님).",
        }

    product = store.find_product(order["product_id"])
    if product is None:
        return {"error": f"주문에 연결된 상품 '{order['product_id']}'를 찾을 수 없습니다."}

    # 재현 가능한 가짜 공급업체 발주번호 생성
    digest = hashlib.sha256(order_id.encode()).hexdigest()[:4].upper()
    supplier_order_no = f"SUP-{digest}"

    order_date = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    expected_delivery = order_date + timedelta(days=product["shipping_days"])

    order["status"] = "placed_with_supplier"
    order["supplier_order_no"] = supplier_order_no
    store.save_orders(orders)

    return {
        "order_id": order_id,
        "status": order["status"],
        "supplier": product["supplier"],
        "supplier_order_no": supplier_order_no,
        "expected_delivery_date": expected_delivery.isoformat(),
    }


def lookup_order_status(order_id: str) -> dict[str, Any]:
    """고객 응대용 주문 상태 조회 (상태를 변경하지 않음)."""
    order = store.find_order(order_id)
    if order is None:
        return {"error": f"주문 ID '{order_id}'를 찾을 수 없습니다. 주문번호를 다시 확인해주세요."}

    product = store.find_product(order["product_id"])
    return {
        "order_id": order["order_id"],
        "product_name": product["name"] if product else order["product_id"],
        "quantity": order["quantity"],
        "status": order["status"],
        "order_date": order["order_date"],
        "supplier_order_no": order["supplier_order_no"],
        "tracking_no": order["tracking_no"],
    }


def get_sales_summary() -> dict[str, Any]:
    """이번 달 누적 매출과 목표 매출 대비 진척률/필요 페이스를 계산한다."""
    orders = store.load_orders()
    today = date.today()
    month_orders = [
        o
        for o in orders
        if datetime.strptime(o["order_date"], "%Y-%m-%d").date().year == today.year
        and datetime.strptime(o["order_date"], "%Y-%m-%d").date().month == today.month
    ]
    revenue_so_far = sum(o["unit_price_krw"] * o["quantity"] for o in month_orders)

    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)
    days_in_month = (next_month_first - date(today.year, today.month, 1)).days
    days_remaining = max((next_month_first - today).days, 0)

    target = config.TARGET_MONTHLY_REVENUE_KRW
    achievement_pct = round(revenue_so_far / target * 100, 1) if target else 0.0
    remaining_amount = max(target - revenue_so_far, 0)
    needed_daily_revenue = (
        math.ceil(remaining_amount / days_remaining) if days_remaining > 0 else remaining_amount
    )

    return {
        "as_of_date": today.isoformat(),
        "orders_this_month": len(month_orders),
        "revenue_so_far_krw": revenue_so_far,
        "target_monthly_revenue_krw": target,
        "achievement_pct": achievement_pct,
        "days_in_month": days_in_month,
        "days_remaining_in_month": days_remaining,
        "needed_daily_revenue_krw": needed_daily_revenue,
    }


# ---------------------------------------------------------------------------
# Claude 도구 스키마 + 디스패치
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "키워드로 소싱 가능한 트렌드 상품을 검색한다. 신규 아이템 리서치나 소싱 후보 "
            "조사를 요청받았을 때 사용한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "검색 키워드 (한글/영문)"},
                "max_results": {
                    "type": "integer",
                    "description": "최대 결과 개수 (기본 5)",
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "calculate_pricing",
        "description": (
            "특정 상품의 공급가/배송비/판매수수료를 반영해 목표 마진율을 달성하는 "
            "권장 판매가와 필요 판매 수량을 계산한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "상품 ID (예: P001)"},
                "target_margin_pct": {
                    "type": "number",
                    "description": "목표 마진율(%). 지정하지 않으면 기본값 사용",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "check_inventory_and_price",
        "description": (
            "상품의 공급가 변동과 재고 수준을 점검해 판매가 재조정이나 재주문이 "
            "필요한지 알려준다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "상품 ID (예: P001)"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "process_order",
        "description": (
            "신규(new) 상태인 주문을 공급업체에 발주 처리하고, 발주번호와 예상 배송 "
            "완료일을 반환한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문 ID (예: O1001)"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "lookup_order_status",
        "description": (
            "고객 문의에 답하기 위해 주문 상태와 배송 정보를 조회한다 (상태를 변경하지 "
            "않는 읽기 전용 조회)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문 ID (예: O1001)"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_sales_summary",
        "description": (
            "이번 달 누적 매출, 목표 매출(월 100만원) 대비 달성률, 목표 달성을 위해 "
            "필요한 일일 매출 페이스를 계산한다."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_SCHEMAS.extend(gmail_tools.GMAIL_TOOL_SCHEMAS)

_TOOL_FUNCS = {
    "search_products": search_products,
    "calculate_pricing": calculate_pricing,
    "check_inventory_and_price": check_inventory_and_price,
    "process_order": process_order,
    "lookup_order_status": lookup_order_status,
    "get_sales_summary": get_sales_summary,
    "send_customization_request": gmail_tools.send_customization_request,
    "search_supplier_emails": gmail_tools.search_supplier_emails,
    "get_thread_summary": gmail_tools.get_thread_summary,
}


def run_tool(name: str, tool_input: dict[str, Any]) -> str:
    """도구를 실행하고 결과를 JSON 문자열로 반환한다. 실패해도 예외를 던지지 않는다."""
    func = _TOOL_FUNCS.get(name)
    if func is None:
        return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
    try:
        result = func(**tool_input)
    except TypeError as e:
        result = {"error": f"잘못된 입력값입니다: {e}"}
    return json.dumps(result, ensure_ascii=False)
