from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import run_ffmpeg

_RATIO_SIZE = {
    "9:16": (1080, 1920),  # Reels / Shorts / TikTok
    "1:1": (1080, 1080),  # 정사각 피드
    "16:9": (1920, 1080),  # YouTube / 가로 피드
    "4:5": (1080, 1350),  # Instagram 세로 피드
}


def export_variant(master_path: Path, ratio: str, out_path: Path) -> Path:
    if ratio not in _RATIO_SIZE:
        raise ValueError(f"지원하지 않는 비율: {ratio} (지원: {list(_RATIO_SIZE)})")
    w, h = _RATIO_SIZE[ratio]
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    run_ffmpeg(
        [
            "-i", str(master_path),
            "-vf", vf,
            "-c:v", "libx264", "-c:a", "aac",
            str(out_path),
        ]
    )
    return out_path
