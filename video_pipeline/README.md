# 영상 자동 생성 파이프라인 (벤더 비종속)

힉스필드(Higgsfield) 같은 특정 AI 영상 생성 서비스에 묶이지 않고, 주제 하나만 넣으면
스토리보드 → 이미지 → 영상 클립 → 나레이션 → 자막 → SNS 규격 export까지 자동으로
처리하는 파이프라인입니다. 각 단계는 "provider" 인터페이스로 분리되어 있어,
설정 파일(`config.yaml`)만 바꾸면 API 없이 로컬로 돌리거나(Mock/Ken Burns) 원하는
AI 서비스(OpenAI, Anthropic, Runway, Kling, Pika, Higgsfield 등)로 그대로 교체할 수 있습니다.

## 파이프라인 구조

```
주제(topic)
  │
  ▼
[1] Script Provider   → 장면별 나레이션 + 이미지 프롬프트 (스토리보드)
  │
  ▼
[2] Image Provider    → 장면별 키프레임 이미지
  │
  ▼
[3] Video Provider    → 키프레임 → 짧은 영상 클립 (AI 생성 or 로컬 Ken Burns)
  │
  ▼
[4] TTS Provider      → 나레이션 음성
  │
  ▼
[5] Assemble          → 클립 + 음성 + 자막 합성 → 장면 연결 → (선택) 배경음악 믹싱
  │
  ▼
[6] Export            → SNS 규격별 영상 (9:16 / 1:1 / 16:9 / 4:5)
```

## 설치

```bash
cd video_pipeline
pip install -r requirements.txt
```

`imageio-ffmpeg`가 정적 ffmpeg 바이너리를 자동으로 받아오므로, 시스템에 ffmpeg를 따로
설치하지 않아도 됩니다.

## 실행 (API 키 없이 바로 테스트)

```bash
python -m pipeline.run --config config.example.yaml
```

기본 설정은 전부 `mock` / `local_kenburns`라서 **외부 API 키 없이도** 끝까지 실행되어
`output/` 아래에 실제 mp4가 생성됩니다(플레이스홀더 이미지 + 무음 타이밍 트랙 + Ken Burns
팬/줌 효과 + 한글 자막 오버레이). 파이프라인 배관 자체가 정상 동작하는지 확인하는 용도입니다.

```
output/
  storyboard.txt            나레이션 + 이미지 프롬프트 텍스트 파일
  scenes/                 장면별 중간 산출물
  master_9x16.mp4          마스터 영상
  export_9x16.mp4          Reels / Shorts / TikTok
  export_1x1.mp4           정사각 피드
  export_16x9.mp4          YouTube / 가로 피드
```

`storyboard.txt`는 스토리보드 생성 직후(1단계)에 매번 자동으로 저장됩니다 — 영상이 완성되기 전에
나레이션/이미지 프롬프트만 먼저 검토하거나 다른 곳에 공유하고 싶을 때 사용하세요.

## 나레이션 언어 (한국어 / 영어)

`language` 설정으로 나레이션 언어를 고릅니다(`mock`, `anthropic` script_provider 둘 다 지원).

```yaml
language: "en"   # "en" | "ko" — 기본값 en
```

- 한국어로 만들고 싶으면 `config.example.yaml`(`language: "ko"`)을 복사해서 사용
- 영어로 만들고 싶으면 `config.example.en.yaml`(`language: "en"`)을 복사해서 사용

```bash
cp config.example.en.yaml config.yaml
# config.yaml의 topic 수정
python -m pipeline.run --config config.yaml
```

이미지 프롬프트(`image_prompt`)는 언어와 무관하게 항상 영어로 생성됩니다 — 대부분의 이미지/영상
생성 API가 영어 프롬프트에서 품질이 더 좋기 때문입니다. `image_prompt`는 화면에 노출되지
않고 생성 API 호출에만 쓰이므로, 나레이션 언어와 분리해도 문제 없습니다.

## 실제 서비스로 교체하기

`config.yaml`에서 4개의 provider를 독립적으로 선택합니다.

| 단계 | provider 값 | 설명 |
|---|---|---|
| script_provider | `mock` \| `anthropic` | `anthropic`은 [Claude API](#script_provider-anthropic-연동) 사용 |
| image_provider | `mock` \| `openai` | `openai`(DALL·E)는 `OPENAI_API_KEY` 필요 |
| video_provider | `local_kenburns` \| `http_generic` | 아래 설명 참고 |
| tts_provider | `mock` \| `openai` | `openai` TTS는 `OPENAI_API_KEY` 필요 |

### script_provider: anthropic 연동

`AnthropicScriptProvider`(`pipeline/providers/script.py`)는 공식 [`anthropic`](https://pypi.org/project/anthropic/)
Python SDK로 Claude를 호출해 주제 하나를 장면별 나레이션 + 이미지 프롬프트로 구조화합니다.
`client.messages.parse()` + Pydantic 스키마(`_Storyboard`)로 응답을 강제 구조화하므로,
JSON 파싱 실패나 텍스트 앞뒤에 붙는 설명 때문에 깨지는 문제가 없습니다.

```yaml
script_provider: anthropic
providers:
  anthropic:
    model: "claude-opus-5"   # 생략 시 기본값
```

**자격증명**: 코드에 키를 하드코딩하지 않습니다. SDK가 아래 순서로 자동 해석합니다.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# 또는
ant auth login   # ~/.config/anthropic/ 에 프로필 저장, SDK가 자동으로 사용
```

```bash
python -m pipeline.run --config config.yaml   # script_provider: anthropic 로 설정된 config
```

인증 실패나 API 오류는 `pipeline/providers/script.py`에서 `anthropic.AuthenticationError` /
`anthropic.APIStatusError`를 잡아 한국어 메시지로 바꿔 올립니다.

### video_provider: 힉스필드가 아니어도 되는 이유

- `local_kenburns`: AI 영상 생성 모델을 아예 쓰지 않고, 정지 이미지에 팬/줌 효과만 입혀
  ffmpeg로 클립을 만듭니다. API 비용 0원, 완전 로컬.
- `http_generic`: Runway, Kling, Pika, Luma, Higgsfield 등 대부분의 image-to-video API가
  따르는 "작업 생성(POST) → 상태 폴링(GET) → 결과 URL 다운로드" 패턴을 범용으로 구현한
  어댑터입니다. `config.yaml`의 `base_url`, `api_key_env`, 필드명만 바꾸면 **코드 수정
  없이** 다른 벤더로 교체됩니다.

```yaml
video_provider: http_generic
providers:
  http_generic:
    base_url: "https://api.<vendor>.com/v1"
    api_key_env: "VIDEO_API_KEY"
    create_field_map:
      model: "..."
      duration: 4
    poll_field: "id"
    status_field: "status"
    result_field: "output_url"
    done_values: ["succeeded", "completed"]
```

특정 벤더의 API가 이 패턴과 다르면(예: 멀티파트가 아닌 JSON body, 다른 인증 방식 등)
`pipeline/providers/video.py`에 `VideoProvider`를 상속하는 클래스를 하나 더 추가하면 됩니다
(예: `RunwayVideoProvider`, `KlingVideoProvider`). `run.py`나 다른 단계는 전혀 손댈 필요가
없습니다 — 이게 이 파이프라인이 "힉스필드가 아니어도" 동작하는 핵심 설계입니다.

## 배경음악 추가

```yaml
providers:
  background_music: "assets/bgm.mp3"
```

## 자막 렌더링 방식

`ffmpeg`의 `drawtext` 필터는 freetype이 포함된 빌드가 필요해 배포 환경마다 지원 여부가
갈립니다. 그래서 이 파이프라인은 자막을 Pillow로 투명 PNG에 직접 그린 뒤 `overlay`
필터로 합성합니다(`pipeline/subtitle.py`) — 어떤 ffmpeg 빌드에서도 동일하게 동작합니다.
한글 렌더링을 위해 `assets/fonts/NanumGothic.ttf`(OFL 라이선스)를 번들로 포함합니다.

## 디렉터리 구조

```
video_pipeline/
  config.example.yaml     한국어 예제 (language: ko)
  config.example.en.yaml  영어 예제 (language: en)
  requirements.txt
  assets/fonts/NanumGothic.ttf
  pipeline/
    models.py            Scene 데이터클래스
    config.py             YAML 설정 로더
    fonts.py               한글 폰트 로더
    subtitle.py            자막 PNG 렌더링
    ffmpeg_utils.py       ffmpeg 바이너리 탐색/실행
    assemble.py            클립+오디오+자막 합성, 장면 연결, 배경음악 믹싱
    export.py              SNS 규격별 export
    run.py                  CLI 진입점 (전체 오케스트레이션)
    providers/
      base.py               Script/Image/Video/TTS 추상 인터페이스
      script.py             mock, anthropic
      image.py               mock, openai
      video.py                local_kenburns, http_generic (벤더 비종속 어댑터)
      tts.py                   mock, openai
```

## 나만의 주제로 실행하기

`config.example.yaml`을 복사해 `topic`, `num_scenes`를 바꾸고 실행합니다.

```bash
cp config.example.yaml config.yaml
# config.yaml의 topic 수정
python -m pipeline.run --config config.yaml
```
