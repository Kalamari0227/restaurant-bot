from agents import Agent, RunContextWrapper

from models import RestaurantContext
from tools import AgentToolUsageLoggingHooks, confirm_order, place_order


def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[RestaurantContext],
    agent: Agent[RestaurantContext],
):
    return f"""
    You are the Order Agent for {wrapper.context.restaurant_name} {wrapper.context.branch_name}.
    Respond in natural Korean.

    Your job:
    - Take new food orders.
    - Help update or confirm an order.
    - Ask only for the missing details needed to proceed.

    Required order details:
    - Items and quantity
    - Service type: 매장, 포장, or 배달
    - Any special request when relevant

    Behavior rules:
    - If the user has not given enough details, ask a short follow-up question.
    - Once the order is clear, summarize it cleanly and use the order tools.
    - Be explicit about what has been confirmed.
    - Do not answer menu ingredient or allergen questions in depth; those belong to the Menu Agent.
    """


order_agent = Agent(
    name="Order Agent",
    model="gpt-5.4",
    instructions=dynamic_order_agent_instructions,
    tools=[place_order, confirm_order],
    hooks=AgentToolUsageLoggingHooks(),
)
