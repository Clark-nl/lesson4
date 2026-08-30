from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

# 한글을 지원하지 않는 PIL 기본 폰트 대신 사용할 번들 폰트 (OFL 라이선스, 나눔고딕).
_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NanumGothic.ttf"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    if _FONT_PATH.exists():
        return ImageFont.truetype(str(_FONT_PATH), size)
    # 폰트 파일이 없는 환경(예: 저장소를 얕게 클론)에서도 깨지지 않도록 폴백.
    return ImageFont.load_default(size=size)
