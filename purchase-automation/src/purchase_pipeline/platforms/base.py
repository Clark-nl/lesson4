"""Abstract interface every sourcing-platform connector must implement.

Adding a new platform (Domeggook, CJdropshipping, ...) means writing one
class here that returns a list of `Product` objects — nothing else in the
pipeline needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from purchase_pipeline.models import Product


class SourcingPlatform(ABC):
    name: str = "base"

    @abstractmethod
    def fetch_catalog(self) -> list[Product]:
        """Return the current catalog snapshot (price, stock, category, ...)."""
        raise NotImplementedError
