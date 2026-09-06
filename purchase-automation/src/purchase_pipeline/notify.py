"""Optional Slack notification after a pipeline run.

Best-effort: a Slack outage must never take down the pipeline run itself,
so network errors here are logged and swallowed rather than raised.
"""

from __future__ import annotations

import logging
import os

from purchase_pipeline.http import get_session

logger = logging.getLogger(__name__)


def notify_slack(message: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set — skipping Slack notification.\n%s", message)
        return

    try:
        resp = get_session().post(webhook_url, json={"text": message}, timeout=15)
        if resp.status_code >= 300:
            logger.warning("Slack notification failed: %s", resp.text)
    except Exception:
        logger.warning("Slack notification failed (network error).", exc_info=True)
