from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Scene


class ScriptProvider(ABC):
    """주제 -> 장면별 나레이션 + 이미지 프롬프트 스토리보드."""

    @abstractmethod
    def generate(self, topic: str, num_scenes: int, language: str) -> list[Scene]: ...


class ImageProvider(ABC):
    """장면 -> 키프레임 이미지."""

    @abstractmethod
    def generate(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path: ...


class VideoProvider(ABC):
    """키프레임 이미지 -> 짧은 영상 클립. AI 영상 생성 모델(Runway/Kling/Higgsfield 등)이나
    로컬 Ken Burns 효과 등 어떤 방식으로 구현해도 되는 교체 가능한 지점."""

    @abstractmethod
    def render(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path: ...


class TTSProvider(ABC):
    """나레이션 텍스트 -> 음성 오디오."""

    @abstractmethod
    def synthesize(self, scene: Scene, out_path: Path) -> Path: ...
