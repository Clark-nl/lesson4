"""Claude 기반 드롭쉬핑 업무 에이전트 (수동 에이전틱 루프)."""

from typing import Any

import anthropic

from . import config, tools

SYSTEM_PROMPT = f"""\
당신은 1인 드롭쉬핑 셀러의 운영을 돕는 AI 비즈니스 에이전트입니다.
이 셀러의 이번 달 목표 매출은 {config.TARGET_MONTHLY_REVENUE_KRW:,}원입니다.

담당 업무:
1. 상품 리서치/소싱 후보 조사 (search_products)
2. 마진을 고려한 가격 책정 (calculate_pricing)
3. 공급가 변동 및 재고 모니터링 (check_inventory_and_price)
4. 신규 주문의 공급업체 발주 처리 (process_order)
5. 고객 문의 응대 - 주문/배송 조회 (lookup_order_status)
6. 매출 현황 및 목표 달성 페이스 보고 (get_sales_summary)
7. 중국 공급업체와의 제품 커스터마이징 협의 - 로고 인쇄, 포장 변경, 색상/사양 변경,
   OEM/ODM 등을 Gmail 이메일로 요청/조회 (send_customization_request,
   search_supplier_emails, get_thread_summary)

원칙:
- 숫자(가격, 매출, 재고 등)는 반드시 도구를 호출해 확인하고, 임의로 추정하지 않는다.
- 상품 ID나 주문 ID가 필요한데 사용자가 이름만 언급했다면 먼저 search_products 등으로 ID를 확인한다.
- 답변은 한국어로, 실무자가 바로 활용할 수 있도록 간결하고 구체적으로 작성한다.
- 고객 응대 시에는 정중하고 친절한 톤을 사용한다.
- 커스터마이징 요청 이메일(send_customization_request)은 실제로 외부 공급업체에
  발송되는 되돌릴 수 없는 행동이다. 먼저 수신자/제목/본문 초안을 한국어로 요약해
  사용자에게 보여주고, 사용자가 명확히 발송을 확정한 경우에만 호출한다.
"""


class DropshippingAgent:
    """대화 기록을 유지하며 도구 호출 루프를 직접 관리하는 에이전트."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic()
        self.messages: list[dict[str, Any]] = []

    def ask(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = self._create_message()
            if response is None:  # API 오류 - 에러 메시지가 이미 반환됨
                return self._last_error
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return self._extract_text(response)

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = tools.run_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                    )
            self.messages.append({"role": "user", "content": tool_results})

    def _create_message(self):
        try:
            return self.client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools.TOOL_SCHEMAS,
                messages=self.messages,
            )
        except anthropic.AuthenticationError:
            self._last_error = "[오류] API 키가 유효하지 않습니다. ANTHROPIC_API_KEY를 확인하세요."
        except anthropic.PermissionDeniedError:
            self._last_error = "[오류] API 키에 필요한 권한이 없습니다."
        except anthropic.NotFoundError:
            self._last_error = "[오류] 요청한 모델을 찾을 수 없습니다."
        except anthropic.RateLimitError:
            self._last_error = "[오류] 요청 한도를 초과했습니다. 잠시 후 다시 시도하세요."
        except anthropic.APIConnectionError:
            self._last_error = "[오류] 네트워크 연결에 실패했습니다."
        except anthropic.APIStatusError as e:
            self._last_error = f"[오류] API 오류가 발생했습니다: {e.message}"
        return None

    @staticmethod
    def _extract_text(response) -> str:
        parts = [block.text for block in response.content if block.type == "text"]
        return "\n".join(parts).strip()
