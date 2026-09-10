"""중국 공급업체와의 제품 커스터마이징 협의를 위한 Gmail 연동 도구.

로고 인쇄, 포장 변경, 색상/사양 변경, OEM/ODM 등 커스터마이징 요청 이메일을
발송하고, 공급업체의 회신을 검색/조회한다. 실제 Gmail 계정에 대한 OAuth 인증이
필요하며(README 참고), 인증 파일이 없으면 에러 메시지를 반환한다(예외를 던지지 않음).
"""

import base64
from email.mime.text import MIMEText
from typing import Any

from .gmail_client import get_gmail_service


def _get_service_or_error() -> tuple[Any, dict[str, Any] | None]:
    """Gmail 서비스 객체를 반환하거나, 실패 시 (None, 에러 딕셔너리)를 반환한다.

    인증 파일 누락(FileNotFoundError)은 안내 메시지를 그대로 전달하고, 그 외
    google-auth/googleapiclient 쪽 문제(패키지 미설치, 손상된 설치, 네트워크 오류 등)는
    일반화된 메시지로 감싼다 - 외부 서비스 연동이라는 시스템 경계이므로 여기서만 폭넓게 처리한다.
    """
    try:
        return get_gmail_service(), None
    except FileNotFoundError as e:
        return None, {"error": str(e)}
    except Exception as e:  # noqa: BLE001 - Gmail 연동은 외부 경계이므로 폭넓게 처리
        return None, {"error": f"Gmail 연동 중 오류가 발생했습니다: {e}"}


def send_customization_request(supplier_email: str, subject: str, body: str) -> dict[str, Any]:
    """중국 공급업체에 제품 커스터마이징 요청 이메일을 Gmail로 발송한다."""
    service, error = _get_service_or_error()
    if error is not None:
        return error

    message = MIMEText(body)
    message["to"] = supplier_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {
        "message_id": sent["id"],
        "thread_id": sent.get("threadId"),
        "to": supplier_email,
        "subject": subject,
    }


def search_supplier_emails(query: str, max_results: int = 10) -> dict[str, Any]:
    """Gmail 검색 문법(from:, subject: 등)으로 공급업체 관련 이메일을 검색한다."""
    service, error = _get_service_or_error()
    if error is not None:
        return error

    listing = (
        service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    )
    message_refs = listing.get("messages", [])

    results = []
    for ref in message_refs:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        results.append(
            {
                "message_id": msg["id"],
                "thread_id": msg["threadId"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
        )
    return {"query": query, "count": len(results), "results": results}


def get_thread_summary(thread_id: str) -> dict[str, Any]:
    """스레드 ID로 공급업체와의 이메일 대화 전체(본문 포함)를 조회한다."""
    service, error = _get_service_or_error()
    if error is not None:
        return error

    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    messages = []
    for msg in thread.get("messages", []):
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        messages.append(
            {
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body_text": _extract_plain_text(msg["payload"]),
            }
        )
    return {"thread_id": thread_id, "message_count": len(messages), "messages": messages}


def _extract_plain_text(payload: dict[str, Any]) -> str:
    """MIME 메시지 payload에서 text/plain 본문을 재귀적으로 추출한다."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="replace"
        )
    for part in payload.get("parts", []):
        text = _extract_plain_text(part)
        if text:
            return text
    return ""


GMAIL_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "send_customization_request",
        "description": (
            "중국 공급업체(제조사)에 제품 커스터마이징(로고 인쇄, 포장 변경, 색상/사양 "
            "변경, OEM/ODM 등) 요청 이메일을 Gmail로 발송한다. 제목과 본문은 호출 전에 "
            "직접 작성한다(영어 권장). 실제로 외부에 발송되는 이메일이므로, 사용자가 "
            "명확히 발송을 확정한 경우에만 호출한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_email": {"type": "string", "description": "공급업체 담당자 이메일 주소"},
                "subject": {"type": "string", "description": "이메일 제목"},
                "body": {"type": "string", "description": "이메일 본문"},
            },
            "required": ["supplier_email", "subject", "body"],
        },
    },
    {
        "name": "search_supplier_emails",
        "description": (
            "Gmail 검색 문법(from:, subject:, 키워드 등)으로 공급업체와 주고받은 이메일을 "
            "검색한다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail 검색 쿼리 (예: 'from:sales@factory.example.com')",
                },
                "max_results": {"type": "integer", "description": "최대 결과 개수 (기본 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_thread_summary",
        "description": "스레드 ID로 공급업체와의 이메일 대화 전체 내용(본문 포함)을 조회한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "Gmail 스레드 ID"},
            },
            "required": ["thread_id"],
        },
    },
]
