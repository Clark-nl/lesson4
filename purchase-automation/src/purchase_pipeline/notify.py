"""Optional Slack notification after a pipeline run."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)


def notify_slack(message: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set — skipping Slack notification.\n%s", message)
        return

    resp = requests.post(webhook_url, json={"text": message}, timeout=15)
    if resp.status_code >= 300:
        logger.warning("Slack notification failed: %s", resp.text)
