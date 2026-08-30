from __future__ import annotations

import json
import os
import re

import requests

from ..models import Scene
from .base import ScriptProvider

_BEATS = ["도입 - 시선을 끄는 훅", "배경 설명", "핵심 내용 전개", "임팩트 있는 장면", "마무리 & CTA"]


class MockScriptProvider(ScriptProvider):
    """외부 API 없이 동작하는 템플릿 기반 스토리보드 생성기."""

    def generate(self, topic: str, num_scenes: int) -> list[Scene]:
        scenes = []
        for i in range(num_scenes):
            beat = _BEATS[i % len(_BEATS)]
            scenes.append(
                Scene(
                    index=i,
                    narration=f"{topic}, {beat}에 대한 나레이션입니다.",
                    image_prompt=f"{topic}, {beat}, cinematic, vertical video still",
                )
            )
        return scenes


class AnthropicScriptProvider(ScriptProvider):
    """Claude API로 실제 스토리보드(나레이션 + 이미지 프롬프트)를 생성."""

    def __init__(self, model: str = "claude-sonnet-5"):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 필요합니다.")

    def generate(self, topic: str, num_scenes: int) -> list[Scene]:
        prompt = (
            f"'{topic}' 주제로 세로형(9:16) SNS 숏폼 영상 스토리보드를 "
            f"정확히 {num_scenes}개 장면으로 만들어줘. "
            "각 장면은 narration(자연스러운 한국어 나레이션 1~2문장)과 "
            "image_prompt(영어, 장면을 그릴 이미지 생성 프롬프트)를 갖는 JSON 배열로만 응답해. "
            '형식: [{"narration": "...", "image_prompt": "..."}, ...]'
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        match = re.search(r"\[.*\]", text, re.S)
        items = json.loads(match.group(0) if match else text)
        return [
            Scene(index=i, narration=item["narration"], image_prompt=item["image_prompt"])
            for i, item in enumerate(items[:num_scenes])
        ]


def get_script_provider(name: str, opts: dict) -> ScriptProvider:
    if name == "mock":
        return MockScriptProvider()
    if name == "anthropic":
        return AnthropicScriptProvider(**opts.get("anthropic", {}))
    raise ValueError(f"알 수 없는 script_provider: {name}")
