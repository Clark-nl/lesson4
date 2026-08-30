from __future__ import annotations

import shutil
import subprocess


def get_ffmpeg_binary() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    found = shutil.which("ffmpeg")
    if found:
        return found

    raise RuntimeError(
        "ffmpeg를 찾을 수 없습니다. `pip install imageio-ffmpeg` 를 설치하거나 "
        "시스템에 ffmpeg를 설치하세요."
    )


def run_ffmpeg(args: list[str]) -> None:
    binary = get_ffmpeg_binary()
    cmd = [binary, "-y", "-loglevel", "error", *args]
    subprocess.run(cmd, check=True)
