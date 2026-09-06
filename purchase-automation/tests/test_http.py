from purchase_pipeline.http import RETRY_STATUS_CODES, get_session, next_page_url


def test_get_session_mounts_retry_adapter_on_both_schemes():
    session = get_session()

    https_adapter = session.get_adapter("https://example.com")
    http_adapter = session.get_adapter("http://example.com")

    assert https_adapter.max_retries.total == 3
    assert set(https_adapter.max_retries.status_forcelist) == set(RETRY_STATUS_CODES)
    assert http_adapter.max_retries.total == 3


def test_next_page_url_parses_link_header():
    class FakeResponse:
        headers = {
            "Link": (
                '<https://x.myshopify.com/admin/api/2024-10/products.json?page_info=abc>; rel="next"'
            )
        }

    assert (
        next_page_url(FakeResponse())
        == "https://x.myshopify.com/admin/api/2024-10/products.json?page_info=abc"
    )


def test_next_page_url_returns_none_without_link_header():
    class FakeResponse:
        headers: dict = {}

    assert next_page_url(FakeResponse()) is None
