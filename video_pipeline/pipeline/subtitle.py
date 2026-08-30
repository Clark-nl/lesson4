from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .fonts import load_font


def render_subtitle_png(text: str, size: tuple[int, int], out_path: Path, font_size: int = 44) -> Path:
    """자막을 투명 배경 PNG로 렌더링. ffmpeg의 overlay 필터로 영상 위에 합성한다.

    (drawtext 필터는 freetype이 빌드된 ffmpeg가 필요해 배포 환경마다 지원 여부가 갈리므로,
    PIL로 직접 그려서 overlay 하는 방식이 더 이식성이 좋다.)
    """
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = load_font(font_size)

    margin = 60
    lines = _wrap_text(text, font, w - 2 * margin, draw)
    line_height = int(font_size * 1.3)
    block_height = line_height * len(lines) + 40
    box_top = h - block_height - 140
    draw.rectangle([0, box_top, w, box_top + block_height], fill=(0, 0, 0, 115))

    y = box_top + 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        draw.text(((w - line_w) / 2, y), line, fill=(255, 255, 255, 255), font=font)
        y += line_height

    img.save(out_path)
    return out_path


def _wrap_text(text: str, font, max_width: float, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
