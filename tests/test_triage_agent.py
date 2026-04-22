import unittest

from models import HandoffData
from my_agents.handoff_utils import format_handoff_message, format_handoff_status


class TriageAgentTests(unittest.TestCase):
    def test_format_handoff_status_maps_complaints_agent(self) -> None:
        input_data = HandoffData(
            to_agent_name="Complaints Agent",
            request_type="complaint",
            request_description="음식과 서비스가 모두 실망스러웠음",
            reason="The user is complaining about a bad dining experience.",
        )

        self.assertEqual(
            format_handoff_status(input_data),
            "불편을 겪으셔서 죄송합니다. 고객 케어 담당이 바로 도와드릴게요...",
        )

    def test_format_handoff_message_uses_restaurant_fields(self) -> None:
        input_data = HandoffData(
            to_agent_name="Menu Agent",
            request_type="menu",
            request_description="채식 메뉴가 있는지 확인",
            reason="The user is asking about available vegetarian dishes.",
        )

        message = format_handoff_message(input_data)

        self.assertIn("Handing off to Menu Agent", message)
        self.assertIn("UI Message: 메뉴 전문가에게 연결합니다...", message)
        self.assertIn(
            "Reason: The user is asking about available vegetarian dishes.",
            message,
        )
        self.assertIn("Request Type: menu", message)
        self.assertIn("Description: 채식 메뉴가 있는지 확인", message)

    def test_format_handoff_status_maps_reservation_agent(self) -> None:
        input_data = HandoffData(
            to_agent_name="Reservation Agent",
            request_type="reservation",
            request_description="4명 저녁 예약",
            reason="The user wants to book a table.",
        )

        self.assertEqual(
            format_handoff_status(input_data),
            "예약 담당에게 연결합니다...",
        )


if __name__ == "__main__":
    unittest.main()
