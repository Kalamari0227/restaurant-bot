import streamlit as st
from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    handoff,
    input_guardrail,
)
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from models import HandoffData, InputGuardrailOutput, RestaurantContext
from output_guardrails import restaurant_output_guardrail
from my_agents.complaints_agent import complaints_agent
from my_agents.handoff_utils import format_handoff_message, format_handoff_status
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent


input_guardrail_agent = Agent(
    name="Restaurant Scope Guardrail",
    model="gpt-5.4",
    instructions="""
    Decide whether the user's message is safe and in scope for a restaurant assistant.

    In scope topics:
    - menu, ingredients, prices, vegetarian options, allergies
    - placing or confirming an order
    - table reservations, reservation changes, availability
    - complaints about food, service, staff behavior, order mistakes, refunds, or manager callbacks

    Small greetings are allowed.

    Mark is_off_topic=true when the message is mainly unrelated to the restaurant.
    Mark contains_inappropriate_language=true when the message includes abusive, threatening,
    hateful, or sexually explicit language, even if it mentions the restaurant.

    Always fill safe_reply:
    - For off-topic requests, explain that you only help with restaurant-related requests such as
      menus, orders, reservations, and complaint support.
    - For inappropriate language, ask the user to rephrase respectfully and explain that you can
      still help with restaurant-related requests once the language is appropriate.

    Keep reason short and specific.
    """,
    output_type=InputGuardrailOutput,
)


@input_guardrail
async def restaurant_scope_guardrail(
    wrapper: RunContextWrapper[RestaurantContext],
    agent: Agent[RestaurantContext],
    input: str,
):
    result = await Runner.run(
        input_guardrail_agent,
        input,
        context=wrapper.context,
    )

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=(
            result.final_output.is_off_topic
            or result.final_output.contains_inappropriate_language
        ),
    )


def dynamic_triage_instructions(
    wrapper: RunContextWrapper[RestaurantContext],
    agent: Agent[RestaurantContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    You are the Triage Agent for {wrapper.context.restaurant_name} {wrapper.context.branch_name}.
    Respond in Korean.

    Your only job is to classify the latest user request and hand off to the right specialist.

    Route to Menu Agent for:
    - menu recommendations
    - ingredients, prices, portion questions
    - vegetarian or vegan options
    - allergy information
    - recommendation requests that mention allergies, dietary restrictions, or companions with food restrictions

    Route to Order Agent for:
    - placing an order
    - confirming, changing, or canceling an order
    - takeout or delivery style requests

    Route to Reservation Agent for:
    - booking a table
    - checking availability
    - changing or canceling a reservation

    Route to Complaints Agent for:
    - dissatisfaction with food quality or service
    - rude staff, poor experience, delayed orders, wrong orders
    - refund requests tied to a bad experience
    - requests to speak with a manager or receive compensation

    Rules:
    - If the user is unhappy or complaining, prioritize Complaints Agent.
    - If routing is clear, hand off immediately.
    - If the domain is clear but the specialist still needs missing details, hand off anyway.
    - Do not ask follow-up questions that belong to the specialist.
    - For allergy-aware or diet-aware menu recommendations, always hand off to Menu Agent first.
    - Do not answer specialist questions yourself once the route is clear.
    - If unclear, ask one short clarifying question.
    - If the user changes topic mid-conversation, route based on the newest request.

    For handoff metadata:
    - to_agent_name: exact specialist agent name
    - request_type: menu, order, reservation, or complaint
    - request_description: brief summary of what the user wants
    - reason: brief reason this specialist is the correct destination
    """


def _render_handoff_status(message: str) -> None:
    handoff_messages = st.session_state.setdefault("handoff_messages", [])
    handoff_messages.append(message)

    placeholder = st.session_state.get("handoff_placeholder")
    if placeholder is None:
        return

    with placeholder.container():
        for handoff_message in handoff_messages:
            st.info(handoff_message)


def handle_handoff(
    wrapper: RunContextWrapper[RestaurantContext],
    input_data: HandoffData,
):
    sidebar_message = format_handoff_message(input_data)
    status_message = format_handoff_status(input_data)
    st.session_state["handoff_target_name"] = input_data.to_agent_name
    st.session_state["handoff_status_message"] = status_message

    with st.sidebar:
        st.write(sidebar_message)

    _render_handoff_status(status_message)


def make_handoff(agent: Agent[RestaurantContext]):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    model="gpt-5.4",
    instructions=dynamic_triage_instructions,
    input_guardrails=[restaurant_scope_guardrail],
    output_guardrails=[restaurant_output_guardrail],
    handoffs=[
        make_handoff(complaints_agent),
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
    ],
)
