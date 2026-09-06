"""CLI entrypoint: fetch catalog -> score -> export -> notify.

Usage:
    python -m purchase_pipeline.pipeline --config config.yaml
    python -m purchase_pipeline.pipeline --config config.yaml --dry-run
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from purchase_pipeline.config import load_config
from purchase_pipeline.exporters import push_draft_products, write_marketplace_csv, write_purchase_list_csv
from purchase_pipeline.notify import notify_slack
from purchase_pipeline.platforms import get_platform
from purchase_pipeline.scoring import score_products

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MARKETPLACE_CHANNELS = {"coupang", "naver", "ebay"}


def run(config_path: str, dry_run: bool = False) -> None:
    config = load_config(config_path)
    platform = get_platform(config.platform)

    logger.info("Fetching catalog from %s ...", platform.name)
    products = platform.fetch_catalog()
    logger.info("Fetched %d products.", len(products))

    items = score_products(products, config)
    logger.info("Scored purchase list: %d rows passed thresholds.", len(items))

    today = date.today().isoformat()
    csv_path = write_purchase_list_csv(items, f"{config.output_dir}/purchase_list_{today}.csv")
    logger.info("Wrote purchase list CSV: %s", csv_path)

    marketplace_paths = []
    for channel in config.channels:
        if channel in MARKETPLACE_CHANNELS:
            path = write_marketplace_csv(
                items, f"{config.output_dir}/{channel}_{today}.csv", channel
            )
            marketplace_paths.append(path)
            logger.info("Wrote %s bulk-upload template: %s", channel, path)

    if "shopify" in config.channels and not dry_run:
        push_draft_products(items, channel="shopify")

    top5 = "\n".join(
        f"- {it.product.name} ({it.channel}): 마진율 {it.margin_rate:.1%}, 예상마진 {it.estimated_margin:,.0f}"
        for it in items[:5]
    )
    notify_slack(
        f"[구매 리스트 자동화] {platform.name} 기준 {len(items)}건 추천 완료 ({today})\n{top5}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sourcing-platform purchase list pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to pipeline config YAML")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip live writes to sales channels (Shopify draft products, etc.)",
    )
    args = parser.parse_args()
    run(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
