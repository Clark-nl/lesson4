from __future__ import annotations

from pathlib import Path

from .ffmpeg_utils import run_ffmpeg
from .models import Scene
from .subtitle import render_subtitle_png


def mux_scene(scene: Scene, out_path: Path, size: tuple[int, int]) -> Path:
    """무음 비디오 클립 + 나레이션 오디오 + 자막(PNG overlay)을 합쳐 장면 클립을 완성."""
    subtitle_path = out_path.with_name(f"{out_path.stem}_subtitle.png")
    render_subtitle_png(scene.narration, size, subtitle_path)
    run_ffmpeg(
        [
            "-i", str(scene.clip_path),
            "-i", str(subtitle_path),
            "-i", str(scene.audio_path),
            "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
            "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            str(out_path),
        ]
    )
    subtitle_path.unlink(missing_ok=True)
    return out_path


def concat_scenes(scene_paths: list[Path], out_path: Path) -> Path:
    list_file = out_path.with_suffix(".txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in scene_paths), encoding="utf-8"
    )
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)])
    list_file.unlink(missing_ok=True)
    return out_path


def add_background_music(video_path: Path, music_path: Path, out_path: Path, music_volume: float = 0.15) -> Path:
    run_ffmpeg(
        [
            "-i", str(video_path),
            "-i", str(music_path),
            "-filter_complex",
            f"[1:a]volume={music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac",
            str(out_path),
        ]
    )
    return out_path
