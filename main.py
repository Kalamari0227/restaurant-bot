import asyncio

import streamlit as st
from agents import Runner, SQLiteSession

from models import RestaurantContext
from my_agents.triage_agent import triage_agent
from settings import load_openai_api_key


st.set_page_config(page_title="Restaurant Bot", page_icon="🍽️")

try:
    load_openai_api_key()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()


st.title("Restaurant Bot")
st.caption("Triage Agent가 메뉴, 주문, 예약 담당으로 handoff하는 레스토랑 봇")


if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "restaurant-bot",
        "restaurant-bot-memory.db",
    )
if "handoff_messages" not in st.session_state:
    st.session_state["handoff_messages"] = []

session = st.session_state["session"]


def write_message_parts(content) -> None:
    if isinstance(content, str):
        st.write(content)
        return

    if not isinstance(content, list):
        return

    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") in {"input_text", "output_text"} and isinstance(
            part.get("text"), str
        ):
            st.write(part["text"].replace("$", "\\$"))


def get_raw_item(item):
    raw_item = item.get("raw_item")
    return raw_item if isinstance(raw_item, dict) else item


async def paint_history() -> None:
    messages = await session.get_items()

    for message in messages:
        if isinstance(message, str) or not isinstance(message, dict):
            continue

        if "role" in message:
            with st.chat_message(message["role"]):
                write_message_parts(message.get("content"))
            continue

        if message.get("type") == "message":
            with st.chat_message("assistant"):
                write_message_parts(message.get("content", []))
            continue

        if message.get("type") == "message_output_item":
            raw_item = get_raw_item(message)
            with st.chat_message("assistant"):
                write_message_parts(raw_item.get("content", []))


asyncio.run(paint_history())


def _handoff_target_name(item) -> str | None:
    target_agent = getattr(item, "target_agent", None)
    if hasattr(target_agent, "name"):
        return target_agent.name
    if isinstance(target_agent, str):
        return target_agent
    return None


async def run_agent(message: str) -> None:
    context = RestaurantContext()

    with st.chat_message("assistant"):
        handoff_placeholder = st.empty()
        text_placeholder = st.empty()
        status_container = st.status("요청을 분류하고 있습니다...", expanded=False)

        st.session_state["handoff_messages"] = []
        st.session_state["handoff_placeholder"] = handoff_placeholder

        response = ""
        stream = Runner.run_streamed(
            triage_agent,
            message,
            context=context,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response.replace("$", "\\$"))
                elif event.data.type == "response.completed":
                    status_container.update(label="응답 완료", state="complete")
            elif event.type == "run_item_stream_event":
                if event.name == "handoff_occured":
                    target_name = _handoff_target_name(event.item)
                    if target_name:
                        status_container.update(
                            label=f"{target_name}로 handoff 중...",
                            state="running",
                        )

        st.session_state.pop("handoff_placeholder", None)


prompt = st.chat_input("메뉴, 주문, 예약에 대해 물어보세요")

if prompt:
    with st.chat_message("user"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    if st.button("Reset memory"):
        asyncio.run(session.clear_session())
        st.session_state["handoff_messages"] = []
        st.rerun()
