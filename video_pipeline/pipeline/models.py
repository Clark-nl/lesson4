from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Scene:
    index: int
    narration: str
    image_prompt: str
    image_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    clip_path: Optional[Path] = None
    duration: Optional[float] = None
