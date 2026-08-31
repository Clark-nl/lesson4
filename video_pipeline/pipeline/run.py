from __future__ import annotations

import argparse
from pathlib import Path

from .assemble import add_background_music, concat_scenes, mux_scene
from .config import Config
from .export import export_variant
from .providers.image import get_image_provider
from .providers.script import get_script_provider
from .providers.tts import get_tts_provider
from .providers.video import get_video_provider
from .storyboard_export import write_storyboard_txt

MASTER_SIZE = (1080, 1920)  # 9:16 마스터 해상도


def run(config_path: str) -> Path:
    cfg = Config.load(config_path)
    out_dir = cfg.output_dir
    scenes_dir = out_dir / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    script_provider = get_script_provider(cfg.script_provider, cfg.providers)
    image_provider = get_image_provider(cfg.image_provider, cfg.providers)
    video_provider = get_video_provider(cfg.video_provider, cfg.providers)
    tts_provider = get_tts_provider(cfg.tts_provider, cfg.providers)

    print(f"[1/5] 스토리보드 생성 중 ({cfg.script_provider}, language={cfg.language})...")
    scenes = script_provider.generate(cfg.topic, cfg.num_scenes, cfg.language)
    storyboard_path = write_storyboard_txt(cfg.topic, scenes, out_dir / "storyboard.txt")
    print(f"  -> {storyboard_path}")

    scene_clip_paths = []
    for scene in scenes:
        print(f"[2/5] 장면 {scene.index + 1}/{len(scenes)} 처리 중 "
              f"(image={cfg.image_provider}, video={cfg.video_provider}, tts={cfg.tts_provider})...")
        scene.audio_path = tts_provider.synthesize(scene, scenes_dir / f"scene_{scene.index}.wav")
        scene.image_path = image_provider.generate(scene, scenes_dir / f"scene_{scene.index}.png", MASTER_SIZE)
        scene.clip_path = video_provider.render(scene, scenes_dir / f"scene_{scene.index}_raw.mp4", MASTER_SIZE)
        final_scene_path = scenes_dir / f"scene_{scene.index}_final.mp4"
        mux_scene(scene, final_scene_path, MASTER_SIZE)
        scene_clip_paths.append(final_scene_path)

    print("[3/5] 장면 연결 중...")
    master_path = out_dir / "master_9x16.mp4"
    concat_scenes(scene_clip_paths, master_path)

    bgm = cfg.providers.get("background_music")
    if bgm:
        print("[4/5] 배경음악 믹싱 중...")
        mixed_path = out_dir / "master_9x16_bgm.mp4"
        add_background_music(master_path, Path(bgm), mixed_path)
        master_path = mixed_path
    else:
        print("[4/5] 배경음악 없음 (건너뜀)")

    print("[5/5] SNS 포맷별 export 중...")
    for ratio in cfg.aspect_ratios:
        safe_ratio = ratio.replace(":", "x")
        export_path = out_dir / f"export_{safe_ratio}.mp4"
        export_variant(master_path, ratio, export_path)
        print(f"  -> {export_path}")

    print(f"완료! 결과물: {out_dir.resolve()}")
    return master_path


def main() -> None:
    parser = argparse.ArgumentParser(description="영상 자동 생성 파이프라인 (힉스필드 비종속)")
    parser.add_argument("--config", default="config.example.yaml", help="설정 YAML 경로")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
