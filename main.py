import asyncio
import html
import sqlite3

import streamlit as st
import streamlit.components.v1 as components
from openai import APIError
from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
)

from models import (
    InputGuardrailOutput,
    RestaurantContext,
    RestaurantOutputGuardrailOutput,
)
from my_agents.handoff_utils import HANDOFF_MESSAGES
from my_agents.triage_agent import triage_agent
from settings import load_openai_api_key


st.set_page_config(
    page_title="Dodam Restaurant Bot",
    page_icon="🍽️",
    layout="wide",
)


SESSION_DB_PATH = "restaurant-bot-memory.db"


AGENT_THEMES = {
    "Assistant": {
        "label": "Assistant",
        "headline": "응답 안내 중",
        "description": "현재 세션에서 생성된 응답입니다.",
        "tone": "ready",
    },
    "Ready": {
        "label": "Ready",
        "headline": "대화를 시작할 준비가 되었습니다.",
        "description": "추천 메뉴, 예약, 주문, 매장 안내를 한 번에 이어서 도와드릴게요.",
        "tone": "ready",
    },
    "Triage Agent": {
        "label": "Triage Agent",
        "headline": "요청을 분류하고 있어요.",
        "description": "가장 잘 맞는 담당 에이전트에게 연결 중입니다.",
        "tone": "triage",
    },
    "Menu Agent": {
        "label": "Menu Agent",
        "headline": "메뉴 안내 중",
        "description": "취향, 알레르기, 추천 메뉴를 기준으로 가장 잘 맞는 선택지를 안내합니다.",
        "tone": "menu",
    },
    "Order Agent": {
        "label": "Order Agent",
        "headline": "주문 처리 중",
        "description": "메뉴 선택과 주문 확인을 빠르게 마무리합니다.",
        "tone": "order",
    },
    "Reservation Agent": {
        "label": "Reservation Agent",
        "headline": "예약 확인 중",
        "description": "인원, 시간, 좌석 조건을 확인해 예약을 도와드립니다.",
        "tone": "reservation",
    },
    "Complaints Agent": {
        "label": "Complaints Agent",
        "headline": "고객 케어 응답 중",
        "description": "불편 사항을 공감하며 해결 옵션이나 에스컬레이션을 안내합니다.",
        "tone": "complaints",
    },
    "Input Guardrail": {
        "label": "Input Guardrail",
        "headline": "입력 가드레일이 안내 중입니다.",
        "description": "레스토랑 관련 요청으로 다시 말씀해 주시면 바로 이어서 도와드릴게요.",
        "tone": "guardrail",
    },
    "Output Guardrail": {
        "label": "Output Guardrail",
        "headline": "출력 가드레일이 응답을 조정했습니다.",
        "description": "안전한 안내 기준을 충족하는 방식으로 다시 도와드릴게요.",
        "tone": "guardrail",
    },
}

FEATURE_ACTIONS = [
    (
        "오늘의 추천",
        "오늘 가장 반응 좋은 메뉴부터 추천해드릴게요.",
        "오늘 추천 메뉴 알려줘",
    ),
    (
        "빠른 주문 전환",
        "바로 주문하실 수 있도록 도와드릴게요.",
        "지금 바로 주문하기 좋은 메뉴 추천해줘",
    ),
    (
        "예약 안내",
        "가능 시간과 인원 조건을 빠르게 확인해드릴게요.",
        "오늘 저녁 예약 가능한 시간 알려줘",
    ),
    (
        "민원 케어",
        "불편 사항을 접수하고 해결 옵션까지 바로 이어드릴게요.",
        "불만 접수하고 싶어요",
    ),
    (
        "매장 정보",
        "영업시간, 위치, 연락처를 한 번에 안내해드릴게요.",
        "매장 위치와 영업시간 알려줘",
    ),
    (
        "직원 연결",
        "사람의 확인이 필요한 요청을 정리해드릴게요.",
        "직원에게 연결하고 싶어요",
    ),
]

DEFAULT_AGENT_STATE = {
    "active_agent_name": "",
    "active_agent_stage": "",
    "active_agent_note": "",
}


def apply_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f7f5f0;
            --panel: rgba(255, 255, 255, 0.96);
            --line: #ded8cc;
            --ink: #25211b;
            --subtle: #70685e;
            --accent: #7d4d23;
            --accent-strong: #553113;
            --accent-soft: #efe3d4;
            --success: #426653;
            --alert: #9a4d2e;
            --slate: #4d5b68;
            --surface: rgba(255, 255, 255, 0.97);
        }

        .stApp {
            background:
                linear-gradient(180deg, #f9f7f2 0%, #f2eee6 100%);
            color: var(--ink) !important;
        }

        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        [data-testid="stMain"] {
            height: 100vh;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        [data-testid="stMainBlockContainer"] {
            background: rgba(255, 255, 255, 0.96) !important;
            border: 1px solid rgba(35, 35, 35, 0.06);
            border-radius: 18px;
            box-shadow: 0 18px 40px rgba(20, 20, 20, 0.05);
            padding: 0.9rem 1rem 7rem !important;
            margin-top: 0.35rem;
            margin-bottom: 1rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(246, 236, 220, 0.98) 0%, rgba(239, 226, 204, 0.96) 100%)
                !important;
            border-right: 1px solid rgba(138, 75, 22, 0.1);
        }

        [data-testid="stSidebarContent"] {
            background: transparent !important;
            padding-top: 1rem;
            height: 100vh;
            overflow-y: auto !important;
        }

        .block-container {
            max-width: 1380px;
            padding-top: 1.2rem;
            padding-bottom: 7.5rem;
        }

        h1, h2, h3, h4 {
            color: var(--ink);
            font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
            letter-spacing: 0;
        }

        p, li, label, [data-testid="stMarkdownContainer"] {
            font-family: "Avenir Next", "Pretendard", "Noto Sans KR", sans-serif;
            color: var(--ink);
        }

        [data-testid="stMainBlockContainer"],
        [data-testid="stMainBlockContainer"] p,
        [data-testid="stMainBlockContainer"] li,
        [data-testid="stMainBlockContainer"] span,
        [data-testid="stMainBlockContainer"] strong,
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] strong {
            color: inherit;
        }

        [data-testid="stChatMessage"] {
            border: none;
            background: transparent;
            box-shadow: none;
            padding: 0;
            margin: 0.35rem 0 0.75rem;
            width: fit-content;
            max-width: min(74%, 780px);
            margin-right: auto;
        }

        [data-testid="stChatMessageContent"] {
            padding-top: 0.15rem;
        }

        [data-testid="stChatMessageAvatar"] {
            display: none;
        }

        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
            border: 1px solid rgba(36, 36, 36, 0.08);
            border-radius: 14px 14px 14px 6px;
            background: #f5f3ee;
            color: var(--ink) !important;
            box-shadow: none;
            padding: 0.72rem 0.96rem 0.82rem;
        }

        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p,
        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] li,
        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] span,
        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] strong {
            color: var(--ink) !important;
        }

        [data-stale="true"] {
            opacity: 1 !important;
            filter: none !important;
        }

        [data-testid="stElementContainer"][data-stale="true"] {
            background: transparent !important;
        }

        .user-bubble {
            width: fit-content;
            max-width: min(70%, 720px);
            margin: 0.35rem 0 0.75rem auto;
            padding: 0.8rem 1rem;
            border: none;
            border-radius: 14px 14px 6px 14px;
            background: #5f3b1b;
            box-shadow: 0 8px 18px rgba(95, 59, 27, 0.14);
            color: #ffffff;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .user-bubble,
        .user-bubble * {
            color: #ffffff !important;
        }

        .composer-shell-anchor,
        .feature-shell-anchor,
        .feature-action-anchor,
        .notice-card {
            border: 1px solid var(--line);
            border-radius: 12px;
            background: var(--panel);
            box-shadow: 0 12px 28px rgba(39, 34, 28, 0.05);
        }

        .feature-shell-anchor {
            display: none;
        }

        [data-testid="stVerticalBlock"]:has(.feature-shell-anchor) {
            margin-bottom: 0.7rem;
        }

        .composer-shell-anchor {
            display: none;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) {
            margin-top: 0.55rem;
            border: none;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            padding: 0;
            position: sticky;
            bottom: 0.55rem;
            z-index: 20;
            backdrop-filter: none;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) form {
            margin-bottom: 0;
            padding: 0.34rem 0.4rem;
            border: 1px solid rgba(24, 24, 24, 0.1);
            border-radius: 999px;
            background: var(--surface);
            box-shadow: 0 10px 30px rgba(24, 24, 24, 0.08);
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) [data-testid="stTextInput"] input {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            color: var(--ink) !important;
            min-height: 2.75rem;
            padding-left: 0.45rem !important;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) [data-testid="stTextInput"] input::placeholder {
            color: var(--subtle) !important;
            opacity: 0.72;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) [data-testid="stTextInput"] > div,
        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) [data-testid="stTextInput"] > div > div {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) [data-testid="stTextInput"] input:focus {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) .stTextInput {
            margin-bottom: 0;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) .stButton > button {
            min-height: 2.5rem;
            border-radius: 999px;
            border: none;
            background: var(--accent-strong);
            color: #ffffff;
            box-shadow: none;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) .stButton > button:hover {
            border: none;
            color: #ffffff;
            background: var(--accent);
        }

        .brand-card {
            display: flex;
            align-items: flex-start;
            flex-direction: column;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
            padding: 0.9rem;
            border: 1px solid rgba(77, 91, 104, 0.12);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: none;
        }

        .brand-card,
        .brand-card * {
            color: var(--ink) !important;
        }

        .brand-copy {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            min-width: 0;
        }

        .brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.6rem;
            height: 2.6rem;
            border-radius: 10px;
            background: #6b4120;
            color: #fffdf8;
            font-size: 1.1rem;
            font-weight: 700;
            flex: 0 0 auto;
        }

        .brand-mark {
            color: #fffdf8 !important;
        }

        .brand-name {
            display: block;
            color: var(--ink);
            font-size: 1.08rem;
            font-weight: 700;
            line-height: 1.2;
            letter-spacing: 0;
        }

        .brand-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.35rem;
        }

        .brand-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.35rem 0.65rem;
            border-radius: 999px;
            border: 1px solid rgba(77, 91, 104, 0.14);
            background: rgba(255, 255, 255, 0.75);
            color: var(--subtle);
            font-size: 0.82rem;
            font-weight: 600;
        }

        .brand-pill {
            color: var(--subtle) !important;
        }

        .feature-card {
            border: none;
            border-radius: 10px;
            background: transparent;
            padding: 0;
        }

        .feature-action-anchor {
            display: none;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) {
            border: 1px solid rgba(24, 24, 24, 0.09);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: none;
            padding: 0.7rem;
            height: 100%;
            display: flex;
            flex-direction: column;
            color: var(--ink) !important;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .feature-card {
            margin-bottom: 0.5rem;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .stButton {
            margin-top: auto;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .stButton > button {
            min-height: 2.25rem;
            border-radius: 8px;
            border: 1px solid rgba(77, 91, 104, 0.14);
            background: #f7f7f5;
            color: var(--ink) !important;
            box-shadow: none;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .stButton > button *,
        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .stButton > button p {
            color: var(--ink) !important;
        }

        [data-testid="stVerticalBlock"]:has(.feature-action-anchor) .stButton > button:hover {
            border-color: rgba(24, 24, 24, 0.14);
            color: #111111;
            background: #fafafa;
        }

        .feature-card strong {
            display: block;
            margin-bottom: 0.24rem;
            color: #151515;
            font-size: 0.92rem;
        }

        .feature-card,
        .feature-card strong,
        .feature-card [data-testid="stMarkdownContainer"],
        .feature-card [data-testid="stMarkdownContainer"] * {
            color: #151515 !important;
        }

        .feature-card span {
            color: #6e6e77;
            font-size: 0.82rem;
            line-height: 1.42;
        }

        .feature-card span {
            color: #6e6e77 !important;
        }

        .sidebar-panel {
            margin-bottom: 0.75rem;
            padding: 0.9rem;
            border: 1px solid rgba(77, 91, 104, 0.12);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.58);
            color: var(--ink) !important;
        }

        .sidebar-panel,
        .sidebar-panel * {
            color: var(--ink) !important;
        }

        .sidebar-title {
            margin: 0 0 0.65rem;
            color: var(--ink);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .sidebar-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.7rem;
            padding: 0.48rem 0;
            border-top: 1px solid rgba(77, 91, 104, 0.1);
            color: var(--subtle);
            font-size: 0.86rem;
        }

        .sidebar-row span {
            color: var(--subtle) !important;
        }

        .sidebar-row:first-of-type {
            border-top: none;
            padding-top: 0;
        }

        .sidebar-row strong {
            color: var(--ink);
            font-size: 0.86rem;
            font-weight: 700;
            text-align: right;
        }

        .status-dot {
            display: inline-flex;
            align-items: center;
            gap: 0.38rem;
        }

        .status-dot::before {
            content: "";
            width: 0.48rem;
            height: 0.48rem;
            border-radius: 50%;
            background: var(--success);
        }

        .agent-badge,
        .inline-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.36rem 0.85rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .badge-ready,
        .tone-ready {
            background: rgba(84, 112, 66, 0.12);
            color: #36512a;
        }

        .badge-triage,
        .tone-triage {
            background: rgba(138, 75, 22, 0.12);
            color: var(--accent);
        }

        .badge-menu,
        .tone-menu {
            background: rgba(152, 94, 38, 0.14);
            color: #7a3d12;
        }

        .badge-order,
        .tone-order {
            background: rgba(84, 108, 145, 0.14);
            color: #29476d;
        }

        .badge-reservation,
        .tone-reservation {
            background: rgba(93, 84, 145, 0.13);
            color: #44348f;
        }

        .badge-complaints,
        .tone-complaints {
            background: rgba(173, 93, 55, 0.14);
            color: #8d3814;
        }

        .badge-guardrail,
        .tone-guardrail {
            background: rgba(158, 109, 53, 0.14);
            color: #7f4e16;
        }

        .agent-inline-status {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin: 0.15rem 0 0.9rem;
            padding: 0.1rem 0.1rem 0.35rem;
            color: var(--subtle);
            font-size: 0.95rem;
            line-height: 1.45;
        }

        .agent-inline-status,
        .agent-inline-status span {
            color: var(--subtle) !important;
        }

        .notice-card {
            padding: 0.9rem 1rem;
            margin-bottom: 0.65rem;
            background: rgba(255, 247, 236, 0.92);
            color: var(--ink) !important;
        }

        .notice-card strong {
            display: block;
            color: var(--alert);
            margin-bottom: 0.18rem;
        }

        .notice-card span {
            color: var(--subtle);
        }

        .handoff-note {
            margin-bottom: 0.65rem;
            padding: 0.75rem 0.9rem;
            border-radius: 16px;
            background: rgba(138, 75, 22, 0.08);
            color: var(--accent);
            font-weight: 600;
        }

        .handoff-note {
            color: var(--accent) !important;
        }

        .progress-note {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            margin: 0.4rem 0 0.6rem;
            color: var(--subtle);
            font-size: 0.9rem;
        }

        .progress-note {
            color: var(--subtle) !important;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid rgba(138, 75, 22, 0.18);
            background: rgba(255, 252, 247, 0.95);
            color: var(--ink);
            font-weight: 600;
            min-height: 2.85rem;
            box-shadow: none;
        }

        .stButton > button,
        .stButton > button * {
            color: var(--ink) !important;
        }

        .stButton > button:hover {
            border-color: rgba(138, 75, 22, 0.38);
            color: var(--accent);
            background: rgba(255, 247, 234, 0.98);
        }

        .user-bubble,
        .user-bubble * {
            color: #ffffff !important;
        }

        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) .stButton > button,
        [data-testid="stVerticalBlock"]:has(.composer-shell-anchor) .stButton > button * {
            color: #ffffff !important;
        }

        [data-testid="stChatInputTextArea"] textarea {
            min-height: 58px;
        }

        @media (max-width: 900px) {
            .user-bubble {
                max-width: 92%;
            }
        }

        @media (max-width: 700px) {
            .brand-copy {
                width: 100%;
            }

            .brand-meta {
                width: 100%;
            }

            [data-testid="stHorizontalBlock"]:has(.feature-action-anchor) {
                flex-direction: column;
            }

            [data-testid="stVerticalBlock"]:has(.feature-action-anchor) {
                margin-bottom: 0.4rem;
                width: 100% !important;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    if "session" not in st.session_state:
        st.session_state["session"] = SQLiteSession(
            "restaurant-bot",
            SESSION_DB_PATH,
        )

    for key, value in DEFAULT_AGENT_STATE.items():
        st.session_state.setdefault(key, value)

    st.session_state.setdefault("handoff_messages", [])
    st.session_state.setdefault("handoff_target_name", "")
    st.session_state.setdefault("handoff_status_message", "")
    st.session_state.setdefault("starter_prompt", None)
    st.session_state.setdefault("pending_user_prompt", None)
    st.session_state.setdefault("scroll_request_nonce", 0)
    st.session_state.setdefault("last_guardrail_type", None)
    st.session_state["message_agent_map"] = load_message_agent_map()


def _with_agent_store(callback):
    connection = sqlite3.connect(SESSION_DB_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_message_agents (
                message_id TEXT PRIMARY KEY,
                agent_name TEXT NOT NULL
            )
            """
        )
        result = callback(connection)
        connection.commit()
        return result
    finally:
        connection.close()


def load_message_agent_map() -> dict[str, str]:
    def _load(connection):
        rows = connection.execute(
            "SELECT message_id, agent_name FROM assistant_message_agents"
        ).fetchall()
        return {message_id: agent_name for message_id, agent_name in rows}

    return _with_agent_store(_load)


def persist_message_agent_map(message_id: str, agent_name: str) -> None:
    def _persist(connection):
        connection.execute(
            """
            INSERT INTO assistant_message_agents (message_id, agent_name)
            VALUES (?, ?)
            ON CONFLICT(message_id) DO UPDATE SET agent_name = excluded.agent_name
            """,
            (message_id, agent_name),
        )

    _with_agent_store(_persist)


def clear_message_agent_map() -> None:
    def _clear(connection):
        connection.execute("DELETE FROM assistant_message_agents")

    _with_agent_store(_clear)


def agent_theme(name: str) -> dict[str, str]:
    return AGENT_THEMES.get(name, AGENT_THEMES["Ready"])


def set_agent_state(name: str, stage: str, note: str) -> None:
    st.session_state["active_agent_name"] = name
    st.session_state["active_agent_stage"] = stage
    st.session_state["active_agent_note"] = note


def agent_summary_html(name: str, stage: str, note: str) -> str:
    theme = agent_theme(name)
    tone = theme["tone"]
    return f"""
    <div class="agent-inline-status">
      <span class="agent-badge badge-{tone}">{theme["label"]}</span>
      <span>{stage}</span>
    </div>
    """


def render_agent_summary(target) -> None:
    if not st.session_state["active_agent_name"]:
        target.empty()
        return

    target.markdown(
        agent_summary_html(
            st.session_state["active_agent_name"],
            st.session_state["active_agent_stage"],
            st.session_state["active_agent_note"],
        ),
        unsafe_allow_html=True,
    )


def render_agent_summaries(targets) -> None:
    for target in targets:
        render_agent_summary(target)


def render_inline_agent_badge(target, name: str) -> None:
    theme = agent_theme(name)
    target.markdown(
        f'<span class="inline-badge badge-{theme["tone"]}">{theme["label"]}</span>',
        unsafe_allow_html=True,
    )


def _message_id_from_payload(message: dict) -> str | None:
    if isinstance(message.get("id"), str):
        return message["id"]

    raw_item = message.get("raw_item")
    if isinstance(raw_item, dict) and isinstance(raw_item.get("id"), str):
        return raw_item["id"]

    return None


def _remember_agent_for_message(message_id: str | None, agent_name: str) -> None:
    if not message_id:
        return

    st.session_state["message_agent_map"][message_id] = agent_name
    persist_message_agent_map(message_id, agent_name)


async def _tag_latest_assistant_message(
    session: SQLiteSession,
    agent_name: str,
) -> None:
    messages = await session.get_items()

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue

        if message.get("role") == "assistant" or message.get("type") in {
            "message",
            "message_output_item",
        }:
            _remember_agent_for_message(_message_id_from_payload(message), agent_name)
            return


def notice_card_html(title: str, message: str) -> str:
    return f"""
    <div class="notice-card">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
    """


def progress_note_html(message: str) -> str:
    return f'<div class="progress-note">• {message}</div>'


def render_feature_strip() -> None:
    feature_shell = st.container()
    with feature_shell:
        st.markdown('<div class="feature-shell-anchor"></div>', unsafe_allow_html=True)

        def _render_action_cell(
            title: str,
            description: str,
            prompt: str,
            key: str,
        ) -> None:
            st.markdown('<div class="feature-action-anchor"></div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="feature-card">
                  <strong>{title}</strong>
                  <span>{description}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("시작", key=key, use_container_width=True):
                st.session_state["starter_prompt"] = prompt

        for row_idx in range(0, len(FEATURE_ACTIONS), 3):
            columns = st.columns(3, gap="small")
            for col_idx, (title, description, prompt) in enumerate(
                FEATURE_ACTIONS[row_idx : row_idx + 3]
            ):
                with columns[col_idx]:
                    _render_action_cell(
                        title,
                        description,
                        prompt,
                        f"feature-action-{row_idx + col_idx}",
                    )


def render_quick_prompt_buttons(prefix: str, prompts: list[tuple[str, str]]) -> None:
    columns = st.columns(len(prompts))
    for idx, (prompt, label) in enumerate(prompts):
        if columns[idx].button(
            label,
            key=f"{prefix}-{idx}",
            use_container_width=True,
        ):
            st.session_state["starter_prompt"] = prompt


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


def text_from_message_content(content) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") in {"input_text", "output_text"} and isinstance(
            part.get("text"), str
        ):
            chunks.append(part["text"])

    return "\n".join(chunk for chunk in chunks if chunk)


def render_user_bubble(content) -> None:
    text = text_from_message_content(content)
    if not text:
        return

    st.markdown(
        f'<div class="user-bubble">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_panel(context: RestaurantContext) -> None:
    active_agent = st.session_state.get("active_agent_name") or "Ready"
    st.markdown(
        f"""
        <div class="brand-card">
          <div class="brand-copy">
            <div class="brand-mark">D</div>
            <div>
              <div class="brand-name">{html.escape(context.restaurant_name)}</div>
              <div class="brand-meta">
                <span class="brand-pill">{html.escape(context.branch_name)}</span>
                <span class="brand-pill">{html.escape(context.phone_number)}</span>
              </div>
            </div>
          </div>
          <span class="brand-pill">Open now</span>
        </div>
        <div class="sidebar-panel">
          <div class="sidebar-title">Conversation</div>
          <div class="sidebar-row">
            <span>Status</span>
            <strong class="status-dot">{html.escape(active_agent)}</strong>
          </div>
          <div class="sidebar-row">
            <span>Branch</span>
            <strong>{html.escape(context.branch_name)}</strong>
          </div>
          <div class="sidebar-row">
            <span>Phone</span>
            <strong>{html.escape(context.phone_number)}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_raw_item(item):
    raw_item = item.get("raw_item")
    return raw_item if isinstance(raw_item, dict) else item


async def paint_history(session: SQLiteSession) -> int:
    messages = await session.get_items()
    rendered = 0

    for message in messages:
        if isinstance(message, str) or not isinstance(message, dict):
            continue

        if "role" in message:
            if message["role"] == "assistant":
                with st.chat_message("assistant"):
                    agent_name = st.session_state["message_agent_map"].get(
                        _message_id_from_payload(message),
                        "Assistant",
                    )
                    render_inline_agent_badge(st, agent_name)
                    write_message_parts(message.get("content"))
            elif message["role"] == "user":
                render_user_bubble(message.get("content"))
            rendered += 1
            continue

        if message.get("type") == "message":
            with st.chat_message("assistant"):
                agent_name = st.session_state["message_agent_map"].get(
                    _message_id_from_payload(message),
                    "Assistant",
                )
                render_inline_agent_badge(st, agent_name)
                write_message_parts(message.get("content", []))
            rendered += 1
            continue

        if message.get("type") == "message_output_item":
            raw_item = get_raw_item(message)
            with st.chat_message("assistant"):
                agent_name = st.session_state["message_agent_map"].get(
                    _message_id_from_payload(message),
                    "Assistant",
                )
                render_inline_agent_badge(st, agent_name)
                write_message_parts(raw_item.get("content", []))
            rendered += 1

    return rendered


def render_sidebar(context: RestaurantContext, session: SQLiteSession):
    with st.sidebar:
        sidebar_summary_placeholder = st.empty()
        render_agent_summary(sidebar_summary_placeholder)
        render_sidebar_panel(context)
        if st.button("Reset memory", key="reset-memory", use_container_width=True):
            asyncio.run(session.clear_session())
            clear_message_agent_map()
            set_agent_state(
                "",
                "대화를 초기화했습니다.",
                "",
            )
            st.session_state["handoff_messages"] = []
            st.session_state["handoff_target_name"] = ""
            st.session_state["handoff_status_message"] = ""
            st.session_state["last_guardrail_type"] = None
            st.session_state["message_agent_map"] = {}
            st.rerun()
    return sidebar_summary_placeholder


def render_auto_scroll_bridge(scroll_request_nonce: int) -> None:
    script = """
        <script>
        const parentWindow = window.parent;
        const parentDocument = parentWindow.document;
        const currentNonce = __SCROLL_NONCE__;

        try {
          if ("scrollRestoration" in parentWindow.history) {
            parentWindow.history.scrollRestoration = "manual";
          }
        } catch (e) {}

        const getMainScroller = () =>
          parentDocument.querySelector('[data-testid="stMain"]') ||
          parentDocument.querySelector('section.main');

        const getSidebarScroller = () =>
          parentDocument.querySelector('[data-testid="stSidebar"] [data-testid="stSidebarContent"]') ||
          parentDocument.querySelector('[data-testid="stSidebar"]');

        const getComposerAnchor = () =>
          parentDocument.querySelector('.composer-shell-anchor');

        const nearBottom = node =>
          !!node && node.scrollHeight - node.scrollTop - node.clientHeight < 96;

        const scrollNodeToBottom = node => {
          if (!node) return;

          if (typeof node.scrollTo === "function") {
            node.scrollTo({ top: node.scrollHeight, behavior: "auto" });
          } else {
            node.scrollTop = node.scrollHeight;
          }
        };

        const scrollToLatest = force => {
          const mainScroller = getMainScroller();
          const sidebarScroller = getSidebarScroller();

          if (force || parentWindow.__restaurantBotStickMain !== false) {
            scrollNodeToBottom(mainScroller);
          }
          if (force || parentWindow.__restaurantBotStickSidebar !== false) {
            scrollNodeToBottom(sidebarScroller);
          }

          const composerAnchor = getComposerAnchor();
          if (composerAnchor && (force || parentWindow.__restaurantBotStickMain !== false)) {
            composerAnchor.scrollIntoView({ behavior: "auto", block: "end" });
          } else if (force) {
            parentWindow.scrollTo({
              top: parentDocument.body.scrollHeight,
              behavior: "auto",
            });
          }
        };

        const scheduleScroll = force => {
          clearTimeout(parentWindow.__restaurantBotScrollTimer);
          parentWindow.__restaurantBotScrollTimer = setTimeout(() => {
            scrollToLatest(force);
            parentWindow.requestAnimationFrame(() => scrollToLatest(force));
          }, 30);
        };

        const reinforceScroll = force => {
          let attempts = 0;
          clearInterval(parentWindow.__restaurantBotScrollInterval);
          parentWindow.__restaurantBotScrollInterval = setInterval(() => {
            scrollToLatest(force);
            attempts += 1;
            if (attempts >= 10) {
              clearInterval(parentWindow.__restaurantBotScrollInterval);
            }
          }, 90);
        };

        const bindStickiness = () => {
          const mainScroller = getMainScroller();
          const sidebarScroller = getSidebarScroller();

          if (mainScroller && mainScroller !== parentWindow.__restaurantBotMainScroller) {
            parentWindow.__restaurantBotMainScroller = mainScroller;
            parentWindow.__restaurantBotStickMain = nearBottom(mainScroller);
            mainScroller.addEventListener("scroll", () => {
              parentWindow.__restaurantBotStickMain = nearBottom(mainScroller);
            }, { passive: true });
          }

          if (sidebarScroller && sidebarScroller !== parentWindow.__restaurantBotSidebarScroller) {
            parentWindow.__restaurantBotSidebarScroller = sidebarScroller;
            parentWindow.__restaurantBotStickSidebar = nearBottom(sidebarScroller);
            sidebarScroller.addEventListener("scroll", () => {
              parentWindow.__restaurantBotStickSidebar = nearBottom(sidebarScroller);
            }, { passive: true });
          }
        };

        bindStickiness();

        const lastHandledNonce = parentWindow.__restaurantBotScrollNonce ?? -1;
        const forceScroll = currentNonce !== lastHandledNonce;
        parentWindow.__restaurantBotScrollNonce = currentNonce;

        if (forceScroll) {
          parentWindow.__restaurantBotStickMain = true;
          parentWindow.__restaurantBotStickSidebar = true;
        }

        scheduleScroll(forceScroll);
        if (forceScroll) {
          reinforceScroll(true);
        }

        parentWindow.addEventListener("load", () => scheduleScroll(false), { once: true });
        parentWindow.addEventListener("pageshow", () => scheduleScroll(false), { once: true });

        if (!parentWindow.__restaurantBotScrollObserver) {
          const appRoot =
            parentDocument.querySelector('.stApp') ||
            parentDocument.body;

          parentWindow.__restaurantBotScrollObserver = new MutationObserver(() => {
            bindStickiness();
            scheduleScroll(false);
          });

          parentWindow.__restaurantBotScrollObserver.observe(appRoot, {
            childList: true,
            subtree: true,
            characterData: true,
          });
        }
        </script>
        """
    script = script.replace("__SCROLL_NONCE__", str(scroll_request_nonce))
    components.html(
        script,
        height=0,
        width=0,
    )


def render_chat_composer() -> None:
    composer_shell = st.container()
    with composer_shell:
        st.markdown('<div class="composer-shell-anchor"></div>', unsafe_allow_html=True)
        with st.form("chat-composer-form", clear_on_submit=True):
            input_col, submit_col = st.columns([7.5, 1.3], gap="small")
            draft = input_col.text_input(
                "메시지 입력",
                placeholder="메뉴, 주문, 예약, 불만 접수에 대해 물어보세요",
                label_visibility="collapsed",
            )
            submitted = submit_col.form_submit_button(
                "보내기",
                use_container_width=True,
            )

    if submitted and draft.strip():
        st.session_state["pending_user_prompt"] = draft.strip()
        st.rerun()


def _handoff_target_name(item) -> str | None:
    target_agent = getattr(item, "target_agent", None)
    if hasattr(target_agent, "name"):
        return target_agent.name
    if isinstance(target_agent, str):
        return target_agent
    return None


def _input_guardrail_message(exc: InputGuardrailTripwireTriggered) -> str:
    output_info = getattr(exc.guardrail_result.output, "output_info", None)
    if isinstance(output_info, InputGuardrailOutput):
        return output_info.safe_reply
    return (
        "저는 레스토랑 관련 질문에 대해서만 도와드리고 있어요. "
        "메뉴 확인, 주문, 예약, 불만 접수와 관련된 요청으로 말씀해 주세요."
    )


def _output_guardrail_message(exc: OutputGuardrailTripwireTriggered) -> str:
    output_info = getattr(exc.guardrail_result.output, "output_info", None)
    if isinstance(output_info, RestaurantOutputGuardrailOutput):
        return output_info.safe_reply
    return (
        "죄송합니다. 방금 답변은 안내 기준을 충족하지 않아 표시하지 않았습니다. "
        "레스토랑 관련 요청으로 다시 말씀해 주세요."
    )


def _api_error_message(exc: APIError) -> str:
    request_id = getattr(exc, "request_id", None)
    suffix = f" 요청 ID: {request_id}" if request_id else ""
    return (
        "현재 AI 응답 처리 중 일시적인 오류가 발생했습니다. "
        "잠시 후 다시 시도해 주세요."
        f"{suffix}"
    )


def _handoff_stage_message(name: str) -> str:
    theme = agent_theme(name)
    return theme["headline"]


async def run_agent(
    message: str,
    session: SQLiteSession,
    summary_placeholders,
) -> None:
    context = RestaurantContext()
    st.session_state["handoff_target_name"] = ""
    st.session_state["handoff_status_message"] = ""

    set_agent_state(
        "Triage Agent",
        "요청을 분류하고 있습니다.",
        "가장 적합한 담당 에이전트로 연결하는 중입니다.",
    )
    render_agent_summaries(summary_placeholders)

    with st.chat_message("assistant"):
        badge_placeholder = st.empty()
        handoff_placeholder = st.empty()
        progress_placeholder = st.empty()
        text_placeholder = st.empty()

        render_inline_agent_badge(badge_placeholder, "Triage Agent")
        progress_placeholder.markdown(
            progress_note_html("요청을 분류하고 있습니다..."),
            unsafe_allow_html=True,
        )

        response = ""

        try:
            stream = Runner.run_streamed(
                triage_agent,
                message,
                context=context,
                session=session,
            )

            async for event in stream.stream_events():
                handoff_target_name = st.session_state.get("handoff_target_name", "")
                if handoff_target_name and handoff_target_name != st.session_state["active_agent_name"]:
                    set_agent_state(
                        handoff_target_name,
                        _handoff_stage_message(handoff_target_name),
                        agent_theme(handoff_target_name)["description"],
                    )
                    render_agent_summaries(summary_placeholders)
                    render_inline_agent_badge(badge_placeholder, handoff_target_name)
                    handoff_placeholder.markdown(
                        f'<div class="handoff-note">{st.session_state.get("handoff_status_message") or HANDOFF_MESSAGES.get(handoff_target_name, f"{handoff_target_name}로 연결합니다...")}</div>',
                        unsafe_allow_html=True,
                    )
                    progress_placeholder.markdown(
                        progress_note_html(
                            f"{agent_theme(handoff_target_name)['label']}가 응답을 이어받았습니다."
                        ),
                        unsafe_allow_html=True,
                    )

                if event.type == "raw_response_event":
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\\$"))
                    elif event.data.type == "response.completed":
                        current_agent = (
                            st.session_state.get("handoff_target_name")
                            or st.session_state["active_agent_name"]
                            or "Triage Agent"
                        )
                        await _tag_latest_assistant_message(session, current_agent)
                        progress_placeholder.empty()
                elif event.type == "run_item_stream_event":
                    if event.name == "handoff_occured":
                        target_name = _handoff_target_name(event.item)
                        if target_name:
                            st.session_state["handoff_target_name"] = target_name
                            set_agent_state(
                                target_name,
                                _handoff_stage_message(target_name),
                                agent_theme(target_name)["description"],
                            )
                            render_agent_summaries(summary_placeholders)
                            render_inline_agent_badge(badge_placeholder, target_name)
                            handoff_placeholder.markdown(
                                f'<div class="handoff-note">{HANDOFF_MESSAGES.get(target_name, f"{target_name}로 연결합니다...")}</div>',
                                unsafe_allow_html=True,
                            )
                            progress_placeholder.markdown(
                                progress_note_html(
                                    f"{agent_theme(target_name)['label']}가 응답을 이어받았습니다."
                                ),
                                unsafe_allow_html=True,
                            )
        except InputGuardrailTripwireTriggered as exc:
            safe_reply = _input_guardrail_message(exc)
            set_agent_state(
                "Input Guardrail",
                "입력 가드레일이 작동했습니다.",
                "메뉴, 주문, 예약, 불만 접수 관련 요청으로 바꿔 말씀해 주시면 계속 도와드릴게요.",
            )
            render_agent_summaries(summary_placeholders)
            render_inline_agent_badge(badge_placeholder, "Input Guardrail")
            handoff_placeholder.markdown(
                notice_card_html(
                    "입력 가드레일 안내",
                    "오프토픽이거나 표현이 과한 메시지는 차단하고 안전한 재시도 방향을 안내합니다.",
                ),
                unsafe_allow_html=True,
            )
            progress_placeholder.empty()
            text_placeholder.write(safe_reply)
            st.session_state["last_guardrail_type"] = "input"
        except OutputGuardrailTripwireTriggered as exc:
            safe_reply = _output_guardrail_message(exc)
            set_agent_state(
                "Output Guardrail",
                "출력 가드레일이 응답을 조정했습니다.",
                "내부 정보 노출이나 부적절한 표현을 막기 위해 안전한 응답만 표시합니다.",
            )
            render_agent_summaries(summary_placeholders)
            render_inline_agent_badge(badge_placeholder, "Output Guardrail")
            handoff_placeholder.markdown(
                notice_card_html(
                    "출력 가드레일 안내",
                    "안전한 응답 기준을 통과하지 못한 출력은 숨기고 정제된 안내로 대체합니다.",
                ),
                unsafe_allow_html=True,
            )
            progress_placeholder.empty()
            text_placeholder.write(safe_reply)
            st.session_state["last_guardrail_type"] = "output"
        except APIError as exc:
            set_agent_state(
                st.session_state.get("handoff_target_name") or "Triage Agent",
                "일시적인 API 오류가 발생했습니다.",
                "잠시 후 다시 시도해 주세요.",
            )
            render_agent_summaries(summary_placeholders)
            current_agent = st.session_state.get("handoff_target_name") or "Triage Agent"
            render_inline_agent_badge(badge_placeholder, current_agent)
            handoff_placeholder.empty()
            progress_placeholder.empty()
            text_placeholder.write(_api_error_message(exc))


try:
    load_openai_api_key()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()


apply_custom_css()
init_session_state()

context = RestaurantContext()
session = st.session_state["session"]

render_feature_strip()
sidebar_summary_placeholder = render_sidebar(context, session)

agent_summary_placeholder = st.empty()
render_agent_summary(agent_summary_placeholder)
history_count = asyncio.run(paint_history(session))

queued_prompt = st.session_state.pop("starter_prompt", None)
pending_prompt = st.session_state.pop("pending_user_prompt", None)
user_prompt = pending_prompt or queued_prompt

if user_prompt:
    st.session_state["scroll_request_nonce"] += 1
    render_user_bubble(user_prompt)
    render_auto_scroll_bridge(st.session_state["scroll_request_nonce"])
    asyncio.run(
        run_agent(
        user_prompt,
        session,
        [agent_summary_placeholder, sidebar_summary_placeholder],
        )
    )

render_chat_composer()
render_auto_scroll_bridge(st.session_state["scroll_request_nonce"])
