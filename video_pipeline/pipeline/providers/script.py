from __future__ import annotations

import anthropic
from pydantic import BaseModel

from ..models import Scene
from .base import ScriptProvider

_BEATS = {
    "en": ["opening hook", "context / setup", "main highlight", "peak moment", "wrap-up & CTA"],
    "ko": ["도입 - 시선을 끄는 훅", "배경 설명", "핵심 내용 전개", "임팩트 있는 장면", "마무리 & CTA"],
}


class MockScriptProvider(ScriptProvider):
    """외부 API 없이 동작하는 템플릿 기반 스토리보드 생성기."""

    def generate(self, topic: str, num_scenes: int, language: str) -> list[Scene]:
        beats = _BEATS.get(language, _BEATS["en"])
        scenes = []
        for i in range(num_scenes):
            beat = beats[i % len(beats)]
            if language == "ko":
                narration = f"{topic}, {beat}에 대한 나레이션입니다."
            else:
                narration = f"Narration for {topic} - {beat}."
            scenes.append(
                Scene(
                    index=i,
                    narration=narration,
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

    def generate(self, topic: str, num_scenes: int, language: str) -> list[Scene]:
        narration_language = "English" if language == "en" else "Korean"
        prompt = (
            f"Create a storyboard for a vertical (9:16) short-form social video about "
            f"'{topic}', with exactly {num_scenes} scenes. Each scene needs a narration "
            f"(1-2 natural sentences, in {narration_language}) and an image_prompt "
            "(in English, describing the visual to generate for that scene)."
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
