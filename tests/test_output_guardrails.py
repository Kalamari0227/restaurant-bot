import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models import RestaurantContext, RestaurantOutputGuardrailOutput
import output_guardrails


class RestaurantOutputGuardrailTests(unittest.IsolatedAsyncioTestCase):
    async def test_guardrail_passes_wrapper_context_to_runner(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = RestaurantOutputGuardrailOutput(
            contains_unprofessional_tone=False,
            contains_internal_information=False,
            reason="professional restaurant response",
            safe_reply="메뉴, 주문, 예약, 불만 접수를 도와드릴 수 있어요.",
        )

        with patch(
            "output_guardrails.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ) as mock_run:
            result = await output_guardrails.restaurant_output_guardrail.guardrail_function(
                wrapper,
                object(),
                "불편을 드려 죄송합니다. 원하시는 해결 방법을 알려주세요.",
            )

        mock_run.assert_awaited_once_with(
            output_guardrails.restaurant_output_guardrail_agent,
            "불편을 드려 죄송합니다. 원하시는 해결 방법을 알려주세요.",
            context=wrapper.context,
        )
        self.assertFalse(result.tripwire_triggered)
        self.assertEqual(result.output_info, validation)

    async def test_guardrail_trips_on_unprofessional_output(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = RestaurantOutputGuardrailOutput(
            contains_unprofessional_tone=True,
            contains_internal_information=False,
            reason="dismissive tone",
            safe_reply="죄송합니다. 더 정중한 방식으로 다시 도와드릴게요.",
        )

        with patch(
            "output_guardrails.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ):
            result = await output_guardrails.restaurant_output_guardrail.guardrail_function(
                wrapper,
                object(),
                "그건 저희 문제가 아닙니다.",
            )

        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(result.output_info.reason, "dismissive tone")

    async def test_guardrail_trips_on_internal_information(self) -> None:
        wrapper = SimpleNamespace(context=RestaurantContext())
        validation = RestaurantOutputGuardrailOutput(
            contains_unprofessional_tone=False,
            contains_internal_information=True,
            reason="mentions internal routing",
            safe_reply="죄송합니다. 내부 정보를 제외하고 다시 안내드릴게요.",
        )

        with patch(
            "output_guardrails.Runner.run",
            new=AsyncMock(return_value=SimpleNamespace(final_output=validation)),
        ):
            result = await output_guardrails.restaurant_output_guardrail.guardrail_function(
                wrapper,
                object(),
                "내부 handoff 규칙상 Complaints Agent로 보내겠습니다.",
            )

        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(result.output_info.reason, "mentions internal routing")


if __name__ == "__main__":
    unittest.main()
