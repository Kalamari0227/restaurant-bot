import asyncio

import streamlit as st
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


AGENT_THEMES = {
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

FEATURE_CARDS = [
    ("오늘의 추천", "취향과 상황을 바탕으로 메뉴를 바로 추천합니다."),
    ("빠른 주문 전환", "추천 메뉴에서 바로 주문 의사까지 연결합니다."),
    ("예약 안내", "가능 시간과 좌석 조건을 확인해 예약을 진행합니다."),
    ("민원 케어", "불만 접수, 환불 검토, 매니저 콜백까지 이어집니다."),
    ("매장 정보", "영업시간, 위치, 전화번호를 빠르게 안내합니다."),
]

QUICK_ACTIONS = [
    ("오늘 저녁 추천 메뉴 알려줘", "오늘의 추천"),
    ("비건 메뉴가 있는지 알려줘", "비건 메뉴"),
    ("오늘 저녁 2인 예약 가능해?", "2인 예약"),
    ("매장 위치와 영업시간 알려줘", "위치/영업시간"),
]

WELCOME_ACTIONS = [
    ("오늘의 추천 메뉴 보여줘", "추천 메뉴"),
    ("해산물 알레르기인데 먹을 수 있는 메뉴가 있을까?", "알레르기 안내"),
    ("내일 점심 4인 예약하고 싶어", "예약하기"),
    ("주문한 메뉴가 너무 늦게 나왔어", "불만 접수"),
]

TRUST_ITEMS = [
    ("정확한 메뉴 추천", "취향과 재료 기준으로 선택지를 좁혀드립니다."),
    ("간편한 예약/주문", "메뉴 상세에서 바로 다음 행동으로 넘어갑니다."),
    ("실시간 상담 흐름", "현재 어떤 담당이 답변 중인지 항상 보입니다."),
    ("안전한 응답", "가드레일이 입력과 출력을 함께 점검합니다."),
]

DEFAULT_AGENT_STATE = {
    "active_agent_name": "Ready",
    "active_agent_stage": "무엇을 도와드릴까요?",
    "active_agent_note": "추천 메뉴, 예약, 주문, 민원 접수를 한 화면에서 도와드릴게요.",
}


def apply_custom_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #fbf5eb;
            --panel: rgba(255, 251, 244, 0.92);
            --line: #e6d5bc;
            --ink: #2b180a;
            --subtle: #7d5c3b;
            --accent: #8a4b16;
            --accent-soft: #efe1cc;
            --success: #356a3a;
            --alert: #8c4f24;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255, 244, 229, 0.95), transparent 34%),
                linear-gradient(180deg, #fffaf1 0%, #f8f0e2 100%);
            color: var(--ink);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 1.2rem;
            padding-bottom: 2.6rem;
        }

        h1, h2, h3, h4 {
            color: var(--ink);
            font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
            letter-spacing: -0.02em;
        }

        p, li, label, [data-testid="stMarkdownContainer"] {
            font-family: "Avenir Next", "Pretendard", "Noto Sans KR", sans-serif;
        }

        [data-testid="stChatMessage"] {
            border: 1px solid rgba(138, 75, 22, 0.08);
            border-radius: 24px;
            background: rgba(255, 252, 247, 0.88);
            box-shadow: 0 18px 50px rgba(89, 54, 19, 0.05);
            padding: 0.35rem 0.45rem;
        }

        [data-testid="stChatMessageContent"] {
            padding-top: 0.2rem;
        }

        .hero-card,
        .section-card,
        .agent-card,
        .trust-card,
        .info-card,
        .notice-card {
            border: 1px solid var(--line);
            border-radius: 28px;
            background: var(--panel);
            box-shadow: 0 24px 60px rgba(107, 68, 26, 0.08);
        }

        .hero-card {
            padding: 1.6rem 1.7rem;
            background:
                radial-gradient(circle at right top, rgba(222, 181, 128, 0.18), transparent 28%),
                linear-gradient(135deg, rgba(255, 250, 241, 0.98), rgba(245, 232, 211, 0.95));
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            background: rgba(138, 75, 22, 0.08);
            color: var(--accent);
            font-size: 0.84rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        .hero-title {
            margin: 0.8rem 0 0.35rem;
            font-size: 3rem;
            line-height: 1.02;
        }

        .hero-subtitle {
            margin: 0;
            max-width: 680px;
            color: var(--subtle);
            font-size: 1.03rem;
            line-height: 1.7;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.9rem;
            margin-top: 1rem;
        }

        .feature-card {
            border: 1px solid rgba(138, 75, 22, 0.12);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.58);
            padding: 1rem;
        }

        .feature-card strong {
            display: block;
            margin-bottom: 0.35rem;
            color: var(--ink);
            font-size: 1rem;
        }

        .feature-card span {
            color: var(--subtle);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .agent-card {
            padding: 1rem 1.15rem;
            margin: 0.8rem 0 1rem;
        }

        .agent-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
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

        .agent-title {
            margin: 0.55rem 0 0.2rem;
            font-size: 1.22rem;
            font-weight: 700;
            color: var(--ink);
        }

        .agent-copy {
            margin: 0;
            color: var(--subtle);
            line-height: 1.55;
        }

        .section-card,
        .trust-card,
        .info-card {
            padding: 1.1rem 1.2rem;
        }

        .section-heading {
            margin-bottom: 0.75rem;
        }

        .section-heading h3 {
            margin: 0;
            font-size: 1.28rem;
        }

        .section-heading p {
            margin: 0.25rem 0 0;
            color: var(--subtle);
        }

        .store-meta {
            display: grid;
            gap: 0.7rem;
        }

        .store-item {
            padding: 0.8rem 0.95rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.68);
            border: 1px solid rgba(138, 75, 22, 0.1);
        }

        .store-item strong,
        .trust-pill strong {
            display: block;
            font-size: 0.96rem;
            color: var(--ink);
        }

        .store-item span,
        .trust-pill span {
            display: block;
            margin-top: 0.22rem;
            color: var(--subtle);
            line-height: 1.45;
        }

        .notice-card {
            padding: 0.9rem 1rem;
            margin-bottom: 0.65rem;
            background: rgba(255, 247, 236, 0.92);
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

        .trust-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.85rem;
        }

        .trust-pill {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.65);
            border: 1px solid rgba(138, 75, 22, 0.1);
        }

        .welcome-card {
            border: 1px solid rgba(138, 75, 22, 0.12);
            border-radius: 22px;
            padding: 1rem 1.05rem;
            background: rgba(255, 250, 244, 0.88);
            margin-bottom: 0.6rem;
        }

        .welcome-card h4 {
            margin: 0 0 0.3rem;
            font-size: 1.2rem;
        }

        .welcome-card p {
            margin: 0;
            color: var(--subtle);
            line-height: 1.6;
        }

        .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(138, 75, 22, 0.18);
            background: rgba(255, 252, 247, 0.95);
            color: var(--ink);
            font-weight: 600;
            min-height: 2.85rem;
            box-shadow: none;
        }

        .stButton > button:hover {
            border-color: rgba(138, 75, 22, 0.38);
            color: var(--accent);
            background: rgba(255, 247, 234, 0.98);
        }

        [data-testid="stChatInputTextArea"] textarea {
            min-height: 58px;
        }

        @media (max-width: 900px) {
            .hero-title {
                font-size: 2.35rem;
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
            "restaurant-bot-memory.db",
        )

    for key, value in DEFAULT_AGENT_STATE.items():
        st.session_state.setdefault(key, value)

    st.session_state.setdefault("handoff_messages", [])
    st.session_state.setdefault("starter_prompt", None)
    st.session_state.setdefault("last_guardrail_type", None)


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
    <div class="agent-card tone-{tone}">
      <div class="agent-row">
        <div>
          <span class="agent-badge badge-{tone}">{theme["label"]}</span>
          <div class="agent-title">{stage}</div>
          <p class="agent-copy">{note}</p>
        </div>
      </div>
    </div>
    """


def render_agent_summary(target) -> None:
    target.markdown(
        agent_summary_html(
            st.session_state["active_agent_name"],
            st.session_state["active_agent_stage"],
            st.session_state["active_agent_note"],
        ),
        unsafe_allow_html=True,
    )


def render_inline_agent_badge(target, name: str) -> None:
    theme = agent_theme(name)
    target.markdown(
        f'<span class="inline-badge badge-{theme["tone"]}">{theme["label"]}</span>',
        unsafe_allow_html=True,
    )


def notice_card_html(title: str, message: str) -> str:
    return f"""
    <div class="notice-card">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
    """


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-card">
          <span class="hero-kicker">DODAM RESTAURANT · AI HOST</span>
          <h1 class="hero-title">도담 레스토랑 챗봇</h1>
          <p class="hero-subtitle">
            메뉴 추천부터 주문, 예약, 매장 안내, 불만 접수까지 한 화면에서 이어지는
            서비스형 레스토랑 챗 경험을 제공합니다. 현재 어떤 담당이 응답 중인지
            항상 확인할 수 있도록 구성했습니다.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_columns = st.columns(len(QUICK_ACTIONS))
    for idx, (prompt, label) in enumerate(QUICK_ACTIONS):
        if action_columns[idx].button(
            label,
            key=f"hero-action-{idx}",
            use_container_width=True,
        ):
            st.session_state["starter_prompt"] = prompt


def render_feature_strip() -> None:
    cards = "".join(
        f"""
        <div class="feature-card">
          <strong>{title}</strong>
          <span>{description}</span>
        </div>
        """
        for title, description in FEATURE_CARDS
    )
    st.markdown(
        f"""
        <div class="section-card">
          <div class="section-heading">
            <h3>핵심 이용 흐름</h3>
            <p>추천 대화와 specialist handoff를 중심으로 빠른 액션을 설계했습니다.</p>
          </div>
          <div class="feature-grid">{cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
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
            with st.chat_message(message["role"]):
                write_message_parts(message.get("content"))
            rendered += 1
            continue

        if message.get("type") == "message":
            with st.chat_message("assistant"):
                write_message_parts(message.get("content", []))
            rendered += 1
            continue

        if message.get("type") == "message_output_item":
            raw_item = get_raw_item(message)
            with st.chat_message("assistant"):
                write_message_parts(raw_item.get("content", []))
            rendered += 1

    return rendered


def render_welcome_state() -> None:
    with st.chat_message("assistant"):
        render_inline_agent_badge(st, "Ready")
        st.markdown(
            """
            <div class="welcome-card">
              <h4>도담 레스토랑에 오신 것을 환영합니다.</h4>
              <p>
                원하는 분위기나 식사 목적만 알려주셔도 추천 메뉴를 골라드리고,
                바로 주문이나 예약까지 이어서 도와드릴 수 있어요.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_quick_prompt_buttons("welcome", WELCOME_ACTIONS)


def render_sidebar(context: RestaurantContext, session: SQLiteSession) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="info-card">
              <div class="section-heading">
                <h3>매장 정보</h3>
                <p>위치, 영업시간, 빠른 안내를 한곳에 모았습니다.</p>
              </div>
              <div class="store-meta">
                <div class="store-item">
                  <strong>지점</strong>
                  <span>Nomad Kitchen · Seoul Gangnam</span>
                </div>
                <div class="store-item">
                  <strong>영업시간</strong>
                  <span>매일 11:30 - 22:00 · 브레이크 15:00 - 17:00</span>
                </div>
                <div class="store-item">
                  <strong>연락처</strong>
                  <span>02-555-0199</span>
                </div>
                <div class="store-item">
                  <strong>추천 안내</strong>
                  <span>채식, 알레르기, 예약, 민원 케어까지 한 흐름으로 이어집니다.</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        if st.button("영업시간 묻기", key="sidebar-hours", use_container_width=True):
            st.session_state["starter_prompt"] = "영업시간과 브레이크 타임 알려줘"
        if st.button("위치 안내 받기", key="sidebar-location", use_container_width=True):
            st.session_state["starter_prompt"] = "매장 위치와 전화번호 알려줘"
        if st.button("민원 접수 시작", key="sidebar-complaint", use_container_width=True):
            st.session_state["starter_prompt"] = "주문한 음식이 너무 늦게 나왔어"

        st.write("")
        st.caption(
            f"{context.restaurant_name} {context.branch_name} · 세션 메모리는 현재 브라우저 세션 안에서 유지됩니다."
        )
        if st.button("Reset memory", key="reset-memory", use_container_width=True):
            asyncio.run(session.clear_session())
            set_agent_state(
                "Ready",
                "대화를 초기화했습니다.",
                "새로운 메뉴 추천, 주문, 예약, 민원 접수를 다시 시작할 수 있습니다.",
            )
            st.session_state["handoff_messages"] = []
            st.session_state["last_guardrail_type"] = None
            st.rerun()


def render_trust_section() -> None:
    pills = "".join(
        f"""
        <div class="trust-pill">
          <strong>{title}</strong>
          <span>{description}</span>
        </div>
        """
        for title, description in TRUST_ITEMS
    )

    st.markdown(
        f"""
        <div class="trust-card">
          <div class="section-heading">
            <h3>안심하고 이어지는 응답 구조</h3>
            <p>현재 담당 표시, 가드레일, 세션 메모리를 함께 드러내는 서비스형 챗 UI를 목표로 합니다.</p>
          </div>
          <div class="trust-grid">{pills}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _handoff_stage_message(name: str) -> str:
    theme = agent_theme(name)
    return theme["headline"]


async def run_agent(
    message: str,
    session: SQLiteSession,
    summary_placeholder,
) -> None:
    context = RestaurantContext()
    set_agent_state(
        "Triage Agent",
        "요청을 분류하고 있습니다.",
        "가장 적합한 담당 에이전트로 연결하는 중입니다.",
    )
    render_agent_summary(summary_placeholder)

    with st.chat_message("assistant"):
        badge_placeholder = st.empty()
        note_placeholder = st.empty()
        handoff_placeholder = st.empty()
        text_placeholder = st.empty()
        status_container = st.status(
            "Triage Agent가 요청을 파악하고 있습니다...",
            expanded=False,
        )

        render_inline_agent_badge(badge_placeholder, "Triage Agent")
        note_placeholder.markdown(
            notice_card_html(
                "현재 단계",
                "요청을 파악한 뒤 메뉴, 주문, 예약, 민원 담당 중 가장 적합한 경로로 이어집니다.",
            ),
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
                if event.type == "raw_response_event":
                    if event.data.type == "response.output_text.delta":
                        response += event.data.delta
                        text_placeholder.write(response.replace("$", "\\$"))
                    elif event.data.type == "response.completed":
                        current_agent = st.session_state["active_agent_name"]
                        status_container.update(
                            label=f"{agent_theme(current_agent)['label']} 응답 완료",
                            state="complete",
                        )
                        set_agent_state(
                            current_agent,
                            "응답이 완료되었습니다.",
                            "후속 질문이나 다음 액션도 바로 이어서 도와드릴게요.",
                        )
                        render_agent_summary(summary_placeholder)
                elif event.type == "run_item_stream_event":
                    if event.name == "handoff_occured":
                        target_name = _handoff_target_name(event.item)
                        if target_name:
                            set_agent_state(
                                target_name,
                                _handoff_stage_message(target_name),
                                agent_theme(target_name)["description"],
                            )
                            render_agent_summary(summary_placeholder)
                            render_inline_agent_badge(badge_placeholder, target_name)
                            handoff_placeholder.markdown(
                                f'<div class="handoff-note">{HANDOFF_MESSAGES.get(target_name, f"{target_name}로 연결합니다...")}</div>',
                                unsafe_allow_html=True,
                            )
                            status_container.update(
                                label=f"{agent_theme(target_name)['label']}가 응답을 이어받았습니다.",
                                state="running",
                            )
        except InputGuardrailTripwireTriggered as exc:
            safe_reply = _input_guardrail_message(exc)
            set_agent_state(
                "Input Guardrail",
                "입력 가드레일이 작동했습니다.",
                "메뉴, 주문, 예약, 불만 접수 관련 요청으로 바꿔 말씀해 주시면 계속 도와드릴게요.",
            )
            render_agent_summary(summary_placeholder)
            render_inline_agent_badge(badge_placeholder, "Input Guardrail")
            handoff_placeholder.markdown(
                notice_card_html(
                    "입력 가드레일 안내",
                    "오프토픽이거나 표현이 과한 메시지는 차단하고 안전한 재시도 방향을 안내합니다.",
                ),
                unsafe_allow_html=True,
            )
            text_placeholder.write(safe_reply)
            st.session_state["last_guardrail_type"] = "input"
            status_container.update(label="입력 가드레일 작동", state="error")
        except OutputGuardrailTripwireTriggered as exc:
            safe_reply = _output_guardrail_message(exc)
            set_agent_state(
                "Output Guardrail",
                "출력 가드레일이 응답을 조정했습니다.",
                "내부 정보 노출이나 부적절한 표현을 막기 위해 안전한 응답만 표시합니다.",
            )
            render_agent_summary(summary_placeholder)
            render_inline_agent_badge(badge_placeholder, "Output Guardrail")
            handoff_placeholder.markdown(
                notice_card_html(
                    "출력 가드레일 안내",
                    "안전한 응답 기준을 통과하지 못한 출력은 숨기고 정제된 안내로 대체합니다.",
                ),
                unsafe_allow_html=True,
            )
            text_placeholder.write(safe_reply)
            st.session_state["last_guardrail_type"] = "output"
            status_container.update(label="출력 가드레일 작동", state="error")


try:
    load_openai_api_key()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()


apply_custom_css()
init_session_state()

context = RestaurantContext()
session = st.session_state["session"]

render_hero()
st.write("")
render_feature_strip()
render_sidebar(context, session)

agent_summary_placeholder = st.empty()
render_agent_summary(agent_summary_placeholder)

history_count = asyncio.run(paint_history(session))
if history_count == 0:
    render_welcome_state()

queued_prompt = st.session_state.pop("starter_prompt", None)
prompt = st.chat_input("메뉴, 주문, 예약, 불만 접수에 대해 물어보세요")
user_prompt = prompt or queued_prompt

if user_prompt:
    with st.chat_message("user"):
        st.write(user_prompt)
    asyncio.run(run_agent(user_prompt, session, agent_summary_placeholder))

st.write("")
render_trust_section()
