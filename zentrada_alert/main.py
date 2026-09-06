"""CLI entry point: fetch Zentrada recommendations and email an alert."""
import argparse
import logging
import pathlib

from zentrada_alert import config, notifier
from zentrada_alert.scraper import ZentradaClient, filter_watched, parse_products

logger = logging.getLogger(__name__)


def run(dry_run_fixture: str | None = None) -> None:
    if dry_run_fixture:
        html = pathlib.Path(dry_run_fixture).read_text(encoding="utf-8")
        products = parse_products(html)
    else:
        if not config.ZENTRADA_USERNAME or not config.ZENTRADA_PASSWORD:
            raise RuntimeError(
                "ZENTRADA_USERNAME / ZENTRADA_PASSWORD is not configured (.env)."
            )
        client = ZentradaClient()
        client.login(config.ZENTRADA_USERNAME, config.ZENTRADA_PASSWORD)
        products = client.fetch_expected_purchase_items()

    logger.info("Fetched %d recommended product(s).", len(products))

    watched = filter_watched(products, config.WATCH_KEYWORDS)
    logger.info("%d product(s) matched the watch list.", len(watched))

    notifier.send_alert(watched)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Zentrada expected-purchase-items alert")
    parser.add_argument(
        "--dry-run-fixture",
        help=(
            "Path to a local HTML file to parse instead of logging into the real "
            "site (useful for testing selectors, e.g. tests/fixtures/sample_recommendations.html)"
        ),
    )
    args = parser.parse_args()

    run(dry_run_fixture=args.dry_run_fixture)


if __name__ == "__main__":
    main()
