# 매일 아침 자동화: Higgsfield 영상 생성 → Blotato SNS 자동 업로드

이 폴더의 `higgsfield-blotato-daily-video.json`은 n8n(https://n8n.io)에 바로 임포트할 수 있는
워크플로우 템플릿입니다. 요청하신 4가지 항목을 다음과 같이 매핑했습니다.

| 요청 항목 | 워크플로우 반영 |
|---|---|
| 1. 힉스필드(Higgsfield) 영상 생성 | `Higgsfield - 영상 생성 요청` + `Higgsfield - 상태 확인` 노드 (비동기 생성 → 폴링) |
| 2. 블라토(Blotato) SNS 자동 업로드 | `Blotato - 미디어 업로드` + `Blotato - SNS 자동 게시` 노드 |
| 3. 매일 아침 실행 연계 | `매일 아침 실행` (Schedule Trigger, 기본 cron `0 8 * * *` = 매일 오전 8시) |
| 4. 옴니라우트 연계 | `옴니라우트 연계 (TODO)` NoOp 노드로 자리만 확보. **어떤 서비스인지 아직 확인이 안 되어 실제 연동은 비워뒀습니다.** 정보를 주시면 채워 넣겠습니다. |

## 가져오기(Import) 방법

1. n8n 대시보드 → Workflows → Import from File
2. `higgsfield-blotato-daily-video.json` 선택
3. 아래 Credentials를 등록하고 각 HTTP Request 노드에 연결

## 필요한 Credentials

- **Higgsfield API Key** (Header Auth)
  - https://docs.higgsfield.ai/docs 에서 최신 인증 방식(예: `Authorization: Key {KEY_ID}:{KEY_SECRET}`)과
    실제 생성/상태조회 엔드포인트를 확인해 `REPLACE_WITH_ACTUAL_GENERATE_ENDPOINT`,
    `REPLACE_WITH_STATUS_ENDPOINT` 부분을 교체하세요.
- **Blotato API Key** (Header Auth)
  - https://help.blotato.com/api/start 에서 API 키 발급.
  - 더 쉽게 쓰려면 공식 n8n 커뮤니티 노드 `@blotato/n8n-nodes-blotato`
    (https://github.com/Blotato-Inc/n8n-nodes-blotato) 를 설치해서
    HTTP Request 노드 2개를 해당 전용 노드로 바꿀 수 있습니다.
  - `targets` 배열의 `accountId`는 Blotato 대시보드에서 연결한 SNS 계정 ID로 교체하세요.

## 아직 비어있는 부분

- **옴니라우트**: 정확히 어떤 시스템/서비스인지 확인되지 않아 `NoOp` 자리표시자만 넣었습니다.
  API 문서, Webhook URL, 또는 정확한 서비스명을 알려주시면 실제 연동 노드로 교체하겠습니다.
- **Higgsfield 정확한 엔드포인트/모델명**: 이 세션에서는 해당 문서 도메인에 대한 외부 접속이
  네트워크 정책상 차단되어 있어 최신 스펙을 직접 확인하지 못했습니다. `docs.higgsfield.ai`에서
  본인 계정으로 로그인 후 정확한 엔드포인트와 요청 바디를 확인해 워크플로우에 반영해주세요.
- **영상 주제/프롬프트**: `영상 주제 설정` 노드에 매일 아침 어떤 주제로 만들지 하드코딩되어 있습니다.
  실제 운영 시에는 Google Sheets, Notion, Airtable 등에서 그날의 주제를 읽어오도록 바꾸는 것을 권장합니다.

## 폴링(재시도) 로직

Higgsfield 생성은 비동기이므로 `생성 대기`(30초) → `상태 확인` → `생성 완료?` 조건 분기 구조로
완료될 때까지 반복 폴링하도록 구성했습니다. `생성 실패?` 분기는 실패 시 별도 처리(`생성 실패 처리`)로
빠지도록 했습니다. 운영 환경에서는 무한 루프 방지를 위해 최대 재시도 횟수 제한을 추가하는 것을
권장합니다.
