from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

import requests

from ..models import Scene
from .base import TTSProvider

WORDS_PER_SECOND = 2.3
SAMPLE_RATE = 24000


class MockTTSProvider(TTSProvider):
    """실제 음성 없이, 나레이션 길이에 맞춰 타이밍용 무음 WAV를 생성.

    scene.duration이 이미 지정되어 있으면(예: 대본에 타임코드가 있는 경우)
    그 값을 그대로 쓰고, 없으면 단어 수 기반으로 추정한다.
    """

    def synthesize(self, scene: Scene, out_path: Path) -> Path:
        if scene.duration is not None:
            duration = scene.duration
        else:
            n_words = max(1, len(scene.narration.split()))
            duration = max(1.5, n_words / WORDS_PER_SECOND)
        n_frames = int(SAMPLE_RATE * duration)
        with wave.open(str(out_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))
        scene.duration = duration
        return out_path


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS API로 실제 나레이션 음성을 생성."""

    def __init__(self, model: str = "tts-1", voice: str = "alloy"):
        self.model = model
        self.voice = voice
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 필요합니다.")

    def synthesize(self, scene: Scene, out_path: Path) -> Path:
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "voice": self.voice,
                "input": scene.narration,
                "response_format": "wav",
            },
            timeout=60,
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        with wave.open(str(out_path), "rb") as wf:
            scene.duration = wf.getnframes() / wf.getframerate()
        return out_path


def get_tts_provider(name: str, opts: dict) -> TTSProvider:
    if name == "mock":
        return MockTTSProvider()
    if name == "openai":
        return OpenAITTSProvider(**opts.get("openai_tts", {}))
    raise ValueError(f"알 수 없는 tts_provider: {name}")
