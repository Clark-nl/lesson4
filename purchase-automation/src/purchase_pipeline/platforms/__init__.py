from purchase_pipeline.platforms.base import SourcingPlatform
from purchase_pipeline.platforms.bigbuy import BigBuyPlatform
from purchase_pipeline.platforms.ownerclan import OwnerClanPlatform

_REGISTRY: dict[str, type] = {
    "ownerclan": OwnerClanPlatform,
    "bigbuy": BigBuyPlatform,
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


__all__ = ["SourcingPlatform", "OwnerClanPlatform", "BigBuyPlatform", "get_platform"]
