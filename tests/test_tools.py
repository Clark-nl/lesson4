"""API 키 없이 도구 로직만 검증하는 오프라인 테스트.

실행: python -m tests.test_tools
"""

import copy
import json

from dropshipping_agent import config, store, tools


def test_search_products_finds_by_keyword():
    result = tools.search_products("이어폰")
    assert result["count"] >= 1
    assert any(r["id"] == "P001" for r in result["results"])


def test_calculate_pricing_meets_margin_target():
    result = tools.calculate_pricing("P001", target_margin_pct=30)
    assert "error" not in result
    price = result["recommended_selling_price_krw"]
    profit = result["estimated_profit_per_unit_krw"]
    # 이익률이 대략 목표 마진율 근방인지 확인 (반올림 오차 허용)
    assert abs(profit / price * 100 - 30) < 2


def test_calculate_pricing_unknown_product():
    result = tools.calculate_pricing("P999")
    assert "error" in result


def test_check_inventory_flags_price_increase_and_low_stock():
    p001 = tools.check_inventory_and_price("P001")  # 공급가 8500 -> 9200 (+8.2%)
    assert p001["needs_attention"] is True
    assert p001["price_change_pct"] > config.PRICE_ALERT_THRESHOLD_PCT

    p006 = tools.check_inventory_and_price("P006")  # stock=3 <= threshold=10
    assert p006["needs_attention"] is True


def test_process_order_updates_status_and_restores_state():
    original_orders = store.load_orders()
    backup = copy.deepcopy(original_orders)
    try:
        result = tools.process_order("O1004")
        assert result["status"] == "placed_with_supplier"
        assert result["supplier_order_no"].startswith("SUP-")

        # 이미 처리된 주문을 다시 처리하면 에러 없이 안내 메시지를 반환
        second = tools.process_order("O1004")
        assert second["status"] == "placed_with_supplier"
        assert "이미 처리된 주문" in second["message"]
    finally:
        store.save_orders(backup)  # 테스트가 데이터 파일을 오염시키지 않도록 복원


def test_lookup_order_status_unknown_order():
    result = tools.lookup_order_status("O9999")
    assert "error" in result


def test_get_sales_summary_shape():
    result = tools.get_sales_summary()
    assert result["target_monthly_revenue_krw"] == config.TARGET_MONTHLY_REVENUE_KRW
    assert result["revenue_so_far_krw"] >= 0
    assert 0 <= result["achievement_pct"]


def test_run_tool_returns_json_string():
    raw = tools.run_tool("get_sales_summary", {})
    parsed = json.loads(raw)
    assert "revenue_so_far_krw" in parsed


def _all_tests():
    return [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]


def main() -> None:
    failures = 0
    for test in _all_tests():
        try:
            test()
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {test.__name__}: {e}")
        else:
            print(f"OK:   {test.__name__}")
    if failures:
        raise SystemExit(f"\n{failures}개 테스트 실패")
    print("\n모든 테스트 통과")


if __name__ == "__main__":
    main()
