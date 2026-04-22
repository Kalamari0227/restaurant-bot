from pydantic import BaseModel


class RestaurantContext(BaseModel):
    restaurant_name: str = "Nomad Kitchen"
    branch_name: str = "Seoul Gangnam"
    phone_number: str = "02-555-0199"


class InputGuardrailOutput(BaseModel):
    is_off_topic: bool
    contains_inappropriate_language: bool = False
    reason: str
    safe_reply: str


class HandoffData(BaseModel):
    to_agent_name: str
    request_type: str
    request_description: str
    reason: str


class RestaurantOutputGuardrailOutput(BaseModel):
    contains_unprofessional_tone: bool
    contains_internal_information: bool
    reason: str
    safe_reply: str = (
        "죄송합니다. 방금 생성된 답변은 안내 기준을 충족하지 않아 표시하지 않았습니다. "
        "메뉴, 주문, 예약, 불만 접수와 관련된 요청으로 다시 말씀해 주세요."
    )


# Backward-compatible alias for older imports in this repo.
UserAccountContext = RestaurantContext
