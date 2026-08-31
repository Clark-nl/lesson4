from __future__ import annotations

from pathlib import Path

from .models import Scene


def write_storyboard_txt(topic: str, scenes: list[Scene], out_path: Path) -> Path:
    """스토리보드(나레이션 + 이미지 프롬프트)를 사람이 읽기 좋은 텍스트 파일로 저장."""
    lines = [f"Topic: {topic}", f"Scenes: {len(scenes)}", ""]
    for scene in scenes:
        lines.append(f"[Scene {scene.index + 1}]")
        lines.append(f"Narration: {scene.narration}")
        lines.append(f"Image prompt: {scene.image_prompt}")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
