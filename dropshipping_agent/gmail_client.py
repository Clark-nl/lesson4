"""Gmail API OAuth2 인증 및 서비스 클라이언트 생성.

최초 실행 시 브라우저에서 OAuth 동의 화면이 뜨고, 이후에는 저장된 토큰
(token.json)으로 자동 인증한다. credentials.json은 Google Cloud Console에서
발급받은 OAuth 클라이언트(데스크톱 앱) 설정 파일이다.

google-auth/googleapiclient는 이 함수 안에서 지연 임포트한다 - 모듈 최상단에서
임포트하면 해당 패키지가 설치되지 않았거나 깨져 있을 때 Gmail을 전혀 쓰지 않는
다른 도구(상품 리서치, 가격 계산 등)까지 임포트 시점에 죽어버리기 때문이다.
"""

from typing import Any

from . import config


def get_gmail_service() -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Credentials | None = None
    if config.GMAIL_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(config.GMAIL_TOKEN_PATH), config.GMAIL_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.GMAIL_CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail API 인증 파일을 찾을 수 없습니다: {config.GMAIL_CREDENTIALS_PATH}\n"
                    "Google Cloud Console에서 OAuth 클라이언트(데스크톱 앱)를 만들고 "
                    "credentials.json으로 저장한 뒤 프로젝트 루트에 두세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.GMAIL_CREDENTIALS_PATH), config.GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        config.GMAIL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)
