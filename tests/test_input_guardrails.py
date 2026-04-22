import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models import InputGuardrailOutput, RestaurantContext
from my_agents import triage_agent


class RestaurantInputGuardrailTests(unittest.IsolatedAsyncioTestCase):
    async def test_guardrail_passes_wrapper_context_to_runner(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = InputGuardrailOutput(
            is_off_topic=False,
            contains_inappropriate_language=False,
            reason="restaurant request",
            safe_reply="메뉴, 주문, 예약, 불만 접수를 도와드릴 수 있어요.",
        )

        with patch(
            "my_agents.triage_agent.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ) as mock_run:
            result = await triage_agent.restaurant_scope_guardrail.guardrail_function(
                wrapper,
                object(),
                "채식 메뉴 추천해줘",
            )

        mock_run.assert_awaited_once_with(
            triage_agent.input_guardrail_agent,
            "채식 메뉴 추천해줘",
            context=wrapper.context,
        )
        self.assertFalse(result.tripwire_triggered)
        self.assertEqual(result.output_info, validation)

    async def test_guardrail_trips_on_off_topic_message(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = InputGuardrailOutput(
            is_off_topic=True,
            contains_inappropriate_language=False,
            reason="non-restaurant topic",
            safe_reply="저는 레스토랑 관련 질문만 도와드릴 수 있어요.",
        )

        with patch(
            "my_agents.triage_agent.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ):
            result = await triage_agent.restaurant_scope_guardrail.guardrail_function(
                wrapper,
                object(),
                "인생의 의미가 뭐야?",
            )

        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(result.output_info.reason, "non-restaurant topic")

    async def test_guardrail_trips_on_inappropriate_language(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = InputGuardrailOutput(
            is_off_topic=False,
            contains_inappropriate_language=True,
            reason="abusive language",
            safe_reply="표현을 조금만 순화해 주시면 레스토랑 관련 도움을 드릴게요.",
        )

        with patch(
            "my_agents.triage_agent.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ):
            result = await triage_agent.restaurant_scope_guardrail.guardrail_function(
                wrapper,
                object(),
                "직원 진짜 최악이야, 욕설...",
            )

        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(result.output_info.reason, "abusive language")


if __name__ == "__main__":
    unittest.main()
