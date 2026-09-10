"""API 키/Gmail 인증 없이 Gmail 연동 로직만 검증하는 오프라인 테스트.

실행: python -m tests.test_gmail_tools
"""

import base64

from dropshipping_agent import gmail_tools, tools


def test_search_products_includes_supplier_email():
    result = tools.search_products("이어폰")
    assert result["results"][0]["supplier_email"] == "sales@shenzhentech-direct.example.com"


def test_send_customization_request_without_credentials_returns_error():
    # 이 테스트 환경에는 credentials.json이 없으므로 예외 대신 에러 딕셔너리를 반환해야 한다.
    result = gmail_tools.send_customization_request(
        supplier_email="sales@shenzhentech-direct.example.com",
        subject="Logo customization request",
        body="We would like to add our logo to the packaging.",
    )
    assert "error" in result


def test_search_supplier_emails_without_credentials_returns_error():
    result = gmail_tools.search_supplier_emails("from:sales@shenzhentech-direct.example.com")
    assert "error" in result


def test_extract_plain_text_finds_nested_text_part():
    encoded = base64.urlsafe_b64encode(b"Hello supplier").decode()
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": base64.urlsafe_b64encode(b"<p>Hi</p>").decode()}},
            {"mimeType": "text/plain", "body": {"data": encoded}},
        ],
    }
    assert gmail_tools._extract_plain_text(payload) == "Hello supplier"


def test_extract_plain_text_returns_empty_for_no_text_part():
    payload = {"mimeType": "multipart/mixed", "parts": []}
    assert gmail_tools._extract_plain_text(payload) == ""


def test_gmail_tool_schemas_registered_in_dispatch():
    tool_names = {schema["name"] for schema in tools.TOOL_SCHEMAS}
    assert {"send_customization_request", "search_supplier_emails", "get_thread_summary"} <= tool_names


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
