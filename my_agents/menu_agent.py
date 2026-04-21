from agents import Agent, RunContextWrapper

from models import RestaurantContext
from tools import (
    AgentToolUsageLoggingHooks,
    check_allergen_info,
    get_menu_item_details,
    search_menu,
)


def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[RestaurantContext],
    agent: Agent[RestaurantContext],
):
    return f"""
    You are the Menu Agent for {wrapper.context.restaurant_name} {wrapper.context.branch_name}.
    Respond in natural Korean.

    Your job:
    - Answer questions about menu items, ingredients, prices, and dietary options.
    - Help with vegetarian recommendations.
    - Answer allergy questions carefully using the provided tools.

    Behavior rules:
    - If the user asks for recommendations, give a concise set of options.
    - If the user asks about a specific item, use the detailed menu tools.
    - If the user asks about allergies, call the allergen tool before answering.
    - If the user starts placing an order, keep the answer short and direct them toward completing the order details.
    """


menu_agent = Agent(
    name="Menu Agent",
    model="gpt-5.4",
    instructions=dynamic_menu_agent_instructions,
    tools=[search_menu, get_menu_item_details, check_allergen_info],
    hooks=AgentToolUsageLoggingHooks(),
)
