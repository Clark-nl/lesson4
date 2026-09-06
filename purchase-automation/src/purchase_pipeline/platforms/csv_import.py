"""Generic CSV-import sourcing "platform" — no API key or subscription needed.

For when you don't want to (or can't) get API access to anything: many
sites let you export or download a product list as CSV by hand — Syncee's
catalog export, dropXL's feed saved to a file, a wholesaler's "download
price list" button, or just a spreadsheet you typed yourself with
candidate items and their cost/retail price. Point CSV_IMPORT_SOURCE at
it (a local file path, or a public URL such as a Dropbox/Drive "direct
download" link or a Google Sheet published as CSV) and this connector
scores it through the exact same margin/channel pipeline as the API-based
platforms — no credentials, no registration, no cost.

Because the source is "whatever CSV you hand it", there's no schema to
guess here at all (unlike bigbuy.py/dropxl.py, which had to work from an
external, unverified schema) — you set column_map to match your own
file's header row. Re-run the pipeline any time you save a fresh export
over the same path/URL to get updated recommendations.

Mock mode: when no source is configured (or CSV_IMPORT_MOCK=1 is set),
reads `tests/fixtures/csv_import_sample.csv` instead.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from purchase_pipeline.http import get_session
from purchase_pipeline.models import Product
from purchase_pipeline.platforms.csv_utils import DEFAULT_CSV_COLUMN_MAP, parse_csv_products

logger = logging.getLogger(__name__)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "csv_import_sample.csv"
)


class CSVImportPlatform:
    name = "csv_import"

    def __init__(
        self,
        source: str | None = None,
        column_map: dict[str, str] | None = None,
        mock: bool | None = None,
    ):
        self.source = source or os.environ.get("CSV_IMPORT_SOURCE")
        self.column_map = column_map or dict(DEFAULT_CSV_COLUMN_MAP)
        self._session = get_session()

        if mock is None:
            mock = os.environ.get("CSV_IMPORT_MOCK") == "1" or not self.source
        self.mock = mock
        if self.mock:
            logger.info("CSVImportPlatform running in mock mode (fixture data, no file/URL read).")

    def fetch_catalog(self) -> list[Product]:
        text = _FIXTURE_PATH.read_text(encoding="utf-8") if self.mock else self._read_source()
        return parse_csv_products(text, self.column_map, self.name)

    def _read_source(self) -> str:
        if self.source.startswith(("http://", "https://")):
            resp = self._session.get(self.source, timeout=60)
            resp.raise_for_status()
            return resp.text
        return Path(self.source).read_text(encoding="utf-8")
