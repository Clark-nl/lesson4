from __future__ import annotations

import anthropic
from pydantic import BaseModel

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


class _StoryboardScene(BaseModel):
    narration: str
    image_prompt: str


class _Storyboard(BaseModel):
    scenes: list[_StoryboardScene]


class AnthropicScriptProvider(ScriptProvider):
    """Claude API(공식 anthropic SDK)로 실제 스토리보드(나레이션 + 이미지 프롬프트)를 생성.

    자격증명은 SDK가 자동으로 해석한다(ANTHROPIC_API_KEY -> ANTHROPIC_AUTH_TOKEN ->
    `ant auth login` 프로필 순). 키를 직접 하드코딩하지 않는다.
    """

    def __init__(self, model: str = "claude-opus-5"):
        self.model = model
        self.client = anthropic.Anthropic()

    def generate(self, topic: str, num_scenes: int) -> list[Scene]:
        prompt = (
            f"'{topic}' 주제로 세로형(9:16) SNS 숏폼 영상 스토리보드를 "
            f"정확히 {num_scenes}개 장면으로 만들어줘. "
            "각 장면은 narration(자연스러운 한국어 나레이션 1~2문장)과 "
            "image_prompt(영어, 장면을 그릴 이미지 생성 프롬프트)를 가져야 해."
        )
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                output_format=_Storyboard,
            )
        except anthropic.AuthenticationError as e:
            raise RuntimeError(
                "Anthropic 인증에 실패했습니다. ANTHROPIC_API_KEY를 설정하거나 "
                "`ant auth login`으로 로그인하세요."
            ) from e
        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API 오류 ({e.status_code}): {e.message}") from e

        scenes = response.parsed_output.scenes[:num_scenes]
        return [
            Scene(index=i, narration=s.narration, image_prompt=s.image_prompt)
            for i, s in enumerate(scenes)
        ]


def get_script_provider(name: str, opts: dict) -> ScriptProvider:
    if name == "mock":
        return MockScriptProvider()
    if name == "anthropic":
        return AnthropicScriptProvider(**opts.get("anthropic", {}))
    raise ValueError(f"알 수 없는 script_provider: {name}")
