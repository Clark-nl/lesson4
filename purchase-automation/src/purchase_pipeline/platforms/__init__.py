from purchase_pipeline.platforms.base import SourcingPlatform
from purchase_pipeline.platforms.bigbuy import BigBuyPlatform
from purchase_pipeline.platforms.csv_import import CSVImportPlatform
from purchase_pipeline.platforms.dropxl import DropXLPlatform
from purchase_pipeline.platforms.ownerclan import OwnerClanPlatform
from purchase_pipeline.platforms.syncee import SynceePlatform

_REGISTRY: dict[str, type] = {
    "ownerclan": OwnerClanPlatform,
    "bigbuy": BigBuyPlatform,
    "dropxl": DropXLPlatform,
    "syncee": SynceePlatform,
    "csv_import": CSVImportPlatform,
}


def get_platform(name: str) -> SourcingPlatform:
    try:
        platform_cls = _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown platform '{name}'. Available: {', '.join(_REGISTRY)}. "
            "Add a new connector under purchase_pipeline/platforms/ and register it here."
        ) from exc
    return platform_cls()


__all__ = [
    "SourcingPlatform",
    "OwnerClanPlatform",
    "BigBuyPlatform",
    "DropXLPlatform",
    "SynceePlatform",
    "CSVImportPlatform",
    "get_platform",
]
