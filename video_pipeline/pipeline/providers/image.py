from __future__ import annotations

import base64
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from ..fonts import load_font
from ..models import Scene
from .base import ImageProvider

_PALETTE = [
    (233, 79, 55),
    (46, 91, 173),
    (35, 155, 122),
    (219, 141, 27),
    (109, 66, 173),
]


class MockImageProvider(ImageProvider):
    """외부 API 없이 프롬프트 텍스트를 얹은 플레이스홀더 이미지를 생성."""

    def generate(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path:
        color = _PALETTE[scene.index % len(_PALETTE)]
        img = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(img)
        font_size = 48
        font = load_font(font_size)
        margin = 60
        line_height = int(font_size * 1.35)
        lines = _wrap_text(scene.image_prompt, font, size[0] - 2 * margin, draw)
        y = size[1] // 2 - (len(lines) * line_height) // 2
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((size[0] - w) / 2, y), line, fill="white", font=font)
            y += line_height
        img.save(out_path)
        return out_path


def _wrap_text(text: str, font, max_width: float, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class OpenAIImageProvider(ImageProvider):
    """OpenAI Images API(DALL-E)로 실제 이미지를 생성."""

    def __init__(self, model: str = "dall-e-3", size: str = "1024x1792"):
        self.model = model
        self.size = size
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 필요합니다.")

    def generate(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": scene.image_prompt,
                "size": self.size,
                "response_format": "b64_json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        b64 = resp.json()["data"][0]["b64_json"]
        out_path.write_bytes(base64.b64decode(b64))
        return out_path


def get_image_provider(name: str, opts: dict) -> ImageProvider:
    if name == "mock":
        return MockImageProvider()
    if name == "openai":
        return OpenAIImageProvider(**opts.get("openai_image", {}))
    raise ValueError(f"알 수 없는 image_provider: {name}")
