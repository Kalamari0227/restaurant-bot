from agents import Agent, RunContextWrapper

from models import RestaurantContext
from output_guardrails import restaurant_output_guardrail
from tools import (
    AgentToolUsageLoggingHooks,
    check_reservation_availability,
    create_reservation,
)


def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[RestaurantContext],
    agent: Agent[RestaurantContext],
):
    return f"""
    You are the Reservation Agent for {wrapper.context.restaurant_name} {wrapper.context.branch_name}.
    Respond in natural Korean.

    Your job:
    - Help guests book a table.
    - Check table availability.
    - Update or cancel a reservation when asked.

    Required details for a full reservation:
    - party size
    - date
    - time
    - guest name
    - phone number

    Behavior rules:
    - If any detail is missing, ask only for what is missing.
    - Once you have enough information, confirm the reservation clearly.
    - For large groups above 8, explain that phone confirmation is required.
    """


reservation_agent = Agent(
    name="Reservation Agent",
    model="gpt-5.4",
    instructions=dynamic_reservation_agent_instructions,
    tools=[check_reservation_availability, create_reservation],
    hooks=AgentToolUsageLoggingHooks(),
    output_guardrails=[restaurant_output_guardrail],
)
