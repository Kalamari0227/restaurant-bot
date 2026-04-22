from models import HandoffData


HANDOFF_MESSAGES = {
    "Complaints Agent": "불편을 겪으셔서 죄송합니다. 고객 케어 담당이 바로 도와드릴게요...",
    "Menu Agent": "메뉴 전문가에게 연결합니다...",
    "Order Agent": "주문 담당에게 연결합니다...",
    "Reservation Agent": "예약 담당에게 연결합니다...",
}


def format_handoff_status(input_data: HandoffData) -> str:
    return HANDOFF_MESSAGES.get(
        input_data.to_agent_name,
        f"{input_data.to_agent_name}에게 연결합니다...",
    )


def format_handoff_message(input_data: HandoffData) -> str:
    return (
        f"Handing off to {input_data.to_agent_name}\n"
        f"UI Message: {format_handoff_status(input_data)}\n"
        f"Reason: {input_data.reason}\n"
        f"Request Type: {input_data.request_type}\n"
        f"Description: {input_data.request_description}"
    )
