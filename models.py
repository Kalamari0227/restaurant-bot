from pydantic import BaseModel


class RestaurantContext(BaseModel):
    restaurant_name: str = "Nomad Kitchen"
    branch_name: str = "Seoul Gangnam"
    phone_number: str = "02-555-0199"


class InputGuardrailOutput(BaseModel):
    is_off_topic: bool
    reason: str


class HandoffData(BaseModel):
    to_agent_name: str
    request_type: str
    request_description: str
    reason: str


# Backward-compatible alias for older imports in this repo.
UserAccountContext = RestaurantContext
