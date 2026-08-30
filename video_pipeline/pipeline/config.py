from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    topic: str
    num_scenes: int = 5
    aspect_ratios: list[str] = field(default_factory=lambda: ["9:16"])
    output_dir: Path = Path("output")
    script_provider: str = "mock"
    image_provider: str = "mock"
    video_provider: str = "local_kenburns"
    tts_provider: str = "mock"
    providers: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        data["output_dir"] = Path(data.get("output_dir", "output"))
        return cls(**data)
