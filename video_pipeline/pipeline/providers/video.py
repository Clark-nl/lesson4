from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import requests

from ..ffmpeg_utils import run_ffmpeg
from ..models import Scene
from .base import VideoProvider


class LocalKenBurnsProvider(VideoProvider):
    """AI 영상 생성 모델 없이, 정지 이미지에 팬/줌(Ken Burns) 효과를 입혀
    ffmpeg만으로 영상 클립을 만드는 완전 무료/로컬 대체 경로. API 키가 전혀 필요 없다."""

    def __init__(self, fps: int = 30):
        self.fps = fps

    def render(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path:
        duration = scene.duration or 4.0
        n_frames = max(1, int(duration * self.fps))
        w, h = size
        zoom_in = scene.index % 2 == 0
        zoom_expr = "min(zoom+0.0015,1.15)" if zoom_in else "if(eq(on,0),1.15,max(zoom-0.0015,1.0))"
        zoompan = f"zoompan=z='{zoom_expr}':d={n_frames}:s={w}x{h}:fps={self.fps}"
        run_ffmpeg(
            [
                "-loop", "1",
                "-i", str(scene.image_path),
                "-vf", zoompan,
                "-t", f"{duration:.3f}",
                "-pix_fmt", "yuv420p",
                str(out_path),
            ]
        )
        return out_path


class HTTPVideoProvider(VideoProvider):
    """특정 벤더에 종속되지 않는 범용 REST image-to-video 어댑터.

    Runway / Kling / Pika / Luma / Higgsfield 등 대부분의 image-to-video API는
    '작업 생성(POST) -> 상태 폴링(GET) -> 결과 URL 다운로드' 패턴을 따른다.
    config.yaml의 base_url / api_key_env / 필드명만 바꾸면 동일 코드로
    다른 벤더를 그대로 붙일 수 있어, 힉스필드가 아니어도(혹은 힉스필드도) 사용 가능하다.
    """

    def __init__(
        self,
        base_url: str,
        api_key_env: str,
        create_field_map: dict[str, Any] | None = None,
        poll_field: str = "id",
        status_field: str = "status",
        result_field: str = "output_url",
        done_values: tuple[str, ...] = ("succeeded", "completed"),
        poll_interval: float = 3.0,
        timeout: float = 300.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise RuntimeError(f"{api_key_env} 환경변수가 필요합니다.")
        self.create_field_map = create_field_map or {}
        self.poll_field = poll_field
        self.status_field = status_field
        self.result_field = result_field
        self.done_values = done_values
        self.poll_interval = poll_interval
        self.timeout = timeout

    def render(self, scene: Scene, out_path: Path, size: tuple[int, int]) -> Path:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"prompt": scene.image_prompt, **self.create_field_map}
        with open(scene.image_path, "rb") as f:
            create = requests.post(
                f"{self.base_url}/generate",
                headers=headers,
                data=payload,
                files={"image": f},
                timeout=60,
            )
        create.raise_for_status()
        task_id = create.json()[self.poll_field]

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            poll = requests.get(f"{self.base_url}/tasks/{task_id}", headers=headers, timeout=30)
            poll.raise_for_status()
            data = poll.json()
            if data.get(self.status_field) in self.done_values:
                video_bytes = requests.get(data[self.result_field], timeout=120).content
                out_path.write_bytes(video_bytes)
                return out_path
            time.sleep(self.poll_interval)
        raise TimeoutError(f"video provider timed out for scene {scene.index}")


def get_video_provider(name: str, opts: dict) -> VideoProvider:
    if name == "local_kenburns":
        return LocalKenBurnsProvider(**opts.get("local_kenburns", {}))
    if name == "http_generic":
        return HTTPVideoProvider(**opts.get("http_generic", {}))
    raise ValueError(f"알 수 없는 video_provider: {name}")
