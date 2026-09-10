"""대화형 CLI로 드롭쉬핑 에이전트를 실행한다."""

import os
import sys

from dotenv import load_dotenv

from . import config
from .agent import DropshippingAgent

EXIT_COMMANDS = {"quit", "exit", "종료"}

DEMO_QUESTIONS = [
    "이어폰 관련해서 소싱할 만한 트렌드 상품 좀 찾아줘",
    "P001 상품을 마진 40%로 팔려면 얼마에 팔아야 해?",
    "P006 재고랑 공급가 상태 좀 확인해줘",
    "O1004 주문 발주 처리해줘",
    "이번 달 매출 목표 대비 지금 얼마나 왔어?",
]


def _check_api_key() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    print(
        "ANTHROPIC_API_KEY가 설정되어 있지 않습니다.\n"
        ".env.example을 .env로 복사한 뒤 발급받은 API 키를 입력하세요.\n"
        "예: cp .env.example .env"
    )
    return False


def run_interactive() -> None:
    agent = DropshippingAgent()
    print("=== 드롭쉬핑 AI 에이전트 ===")
    print(f"이번 달 목표 매출: {config.TARGET_MONTHLY_REVENUE_KRW:,}원")
    print("상품 리서치, 가격 책정, 재고/가격 모니터링, 주문 처리, 고객 응대를 도와드립니다.")
    print("종료하려면 'exit'를 입력하세요.\n")

    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break
        reply = agent.ask(user_input)
        print(f"에이전트> {reply}\n")


def run_demo() -> None:
    agent = DropshippingAgent()
    print("=== 드롭쉬핑 AI 에이전트 데모 ===")
    print(f"이번 달 목표 매출: {config.TARGET_MONTHLY_REVENUE_KRW:,}원\n")
    for question in DEMO_QUESTIONS:
        print(f"나> {question}")
        print(f"에이전트> {agent.ask(question)}\n")


def main() -> None:
    load_dotenv()
    if not _check_api_key():
        sys.exit(1)

    if "--demo" in sys.argv:
        run_demo()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
