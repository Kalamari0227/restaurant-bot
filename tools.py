import streamlit as st
from agents import Agent, AgentHooks, RunContextWrapper, Tool, function_tool

from models import RestaurantContext


MENU_ITEMS = [
    {
        "name": "Burrata Caprese",
        "category": "starter",
        "price": 17000,
        "ingredients": ["burrata", "tomato", "basil", "olive oil"],
        "allergens": ["dairy"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Prosciutto e Melone",
        "category": "starter",
        "price": 18000,
        "ingredients": ["prosciutto", "melon", "olive oil"],
        "allergens": [],
        "tags": ["gluten-free"],
    },
    {
        "name": "Calamari Fritti",
        "category": "starter",
        "price": 19000,
        "ingredients": ["squid", "flour", "lemon", "parsley"],
        "allergens": ["gluten", "shellfish"],
        "tags": [],
    },
    {
        "name": "Bruschetta al Pomodoro",
        "category": "starter",
        "price": 13000,
        "ingredients": ["bread", "tomato", "garlic", "basil", "olive oil"],
        "allergens": ["gluten"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Insalata di Rucola",
        "category": "starter",
        "price": 14000,
        "ingredients": ["arugula", "grana padano", "lemon", "olive oil"],
        "allergens": ["dairy"],
        "tags": ["vegetarian", "gluten-free"],
    },
    {
        "name": "Spaghetti alla Carbonara",
        "category": "main",
        "price": 24000,
        "ingredients": ["spaghetti", "guanciale", "egg", "pecorino romano", "black pepper"],
        "allergens": ["egg", "gluten", "dairy"],
        "tags": [],
    },
    {
        "name": "Tagliatelle al Ragu",
        "category": "main",
        "price": 25000,
        "ingredients": ["tagliatelle", "beef ragu", "tomato", "celery", "carrot"],
        "allergens": ["gluten"],
        "tags": [],
    },
    {
        "name": "Penne all'Arrabbiata",
        "category": "main",
        "price": 22000,
        "ingredients": ["penne", "tomato", "garlic", "chili", "parsley"],
        "allergens": ["gluten"],
        "tags": ["vegan"],
    },
    {
        "name": "Pappardelle ai Funghi",
        "category": "main",
        "price": 24000,
        "ingredients": ["pappardelle", "porcini mushroom", "garlic", "parsley", "cream"],
        "allergens": ["gluten", "dairy"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Lasagna alla Bolognese",
        "category": "main",
        "price": 27000,
        "ingredients": ["pasta sheets", "beef ragu", "bechamel", "parmesan"],
        "allergens": ["gluten", "dairy", "egg"],
        "tags": [],
    },
    {
        "name": "Risotto ai Funghi",
        "category": "main",
        "price": 23000,
        "ingredients": ["arborio rice", "mushroom", "white wine", "parmesan"],
        "allergens": ["dairy"],
        "tags": ["vegetarian", "gluten-free"],
    },
    {
        "name": "Risotto ai Frutti di Mare",
        "category": "main",
        "price": 29000,
        "ingredients": ["arborio rice", "shrimp", "mussel", "clam", "tomato"],
        "allergens": ["shellfish"],
        "tags": ["gluten-free"],
    },
    {
        "name": "Gnocchi al Pesto",
        "category": "main",
        "price": 23000,
        "ingredients": ["potato gnocchi", "basil", "pine nut", "parmesan"],
        "allergens": ["dairy", "tree nuts", "gluten"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Pollo alla Cacciatora",
        "category": "main",
        "price": 28000,
        "ingredients": ["chicken", "tomato", "olive", "caper", "white wine"],
        "allergens": [],
        "tags": ["gluten-free"],
    },
    {
        "name": "Saltimbocca alla Romana",
        "category": "main",
        "price": 32000,
        "ingredients": ["veal", "prosciutto", "sage", "butter", "white wine"],
        "allergens": ["dairy"],
        "tags": ["gluten-free"],
    },
    {
        "name": "Branzino al Forno",
        "category": "main",
        "price": 34000,
        "ingredients": ["sea bass", "lemon", "potato", "olive oil", "herbs"],
        "allergens": ["fish"],
        "tags": ["gluten-free"],
    },
    {
        "name": "Margherita Pizza",
        "category": "main",
        "price": 22000,
        "ingredients": ["pizza dough", "tomato", "mozzarella", "basil"],
        "allergens": ["gluten", "dairy"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Quattro Formaggi Pizza",
        "category": "main",
        "price": 25000,
        "ingredients": ["pizza dough", "mozzarella", "gorgonzola", "fontina", "parmesan"],
        "allergens": ["gluten", "dairy"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Tiramisu",
        "category": "dessert",
        "price": 11000,
        "ingredients": ["mascarpone", "espresso", "savoiardi", "egg", "cocoa"],
        "allergens": ["dairy", "egg", "gluten"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Panna Cotta",
        "category": "dessert",
        "price": 10000,
        "ingredients": ["cream", "vanilla", "berry compote"],
        "allergens": ["dairy"],
        "tags": ["vegetarian", "gluten-free"],
    },
    {
        "name": "Cannoli Siciliani",
        "category": "dessert",
        "price": 11000,
        "ingredients": ["ricotta", "flour", "sugar", "orange zest", "pistachio"],
        "allergens": ["dairy", "gluten", "tree nuts"],
        "tags": ["vegetarian"],
    },
]


def _find_menu_item(item_name: str):
    normalized = item_name.strip().lower()
    for item in MENU_ITEMS:
        if item["name"].lower() == normalized:
            return item
    for item in MENU_ITEMS:
        if normalized in item["name"].lower():
            return item
    return None


def _ordered_menu_item_names(items: str) -> tuple[list[str], list[str]]:
    normalized_order = items.lower()
    found: list[str] = []
    for item in MENU_ITEMS:
        if item["name"].lower() in normalized_order:
            found.append(item["name"])

    unknown_parts = [
        part.strip(" .")
        for part in items.replace("\n", ",").split(",")
        if part.strip(" .")
    ]
    for found_name in found:
        unknown_parts = [
            part
            for part in unknown_parts
            if found_name.lower() not in part.lower()
        ]

    return found, unknown_parts


def _menu_validation_message(items: str) -> str | None:
    found, unknown_parts = _ordered_menu_item_names(items)
    if found and not unknown_parts:
        return None

    if found:
        known = ", ".join(found)
        unknown = ", ".join(unknown_parts)
        return (
            "일부 요청 메뉴를 현재 메뉴에서 확인하지 못했습니다.\n"
            f"- 확인된 메뉴: {known}\n"
            f"- 확인 필요: {unknown}\n"
            "메뉴에 있는 항목만 주문을 도와드릴 수 있습니다. 메뉴명을 다시 확인해 주세요."
        )

    return (
        "요청하신 메뉴를 현재 메뉴에서 확인하지 못했습니다. "
        "메뉴에 있는 항목만 주문을 도와드릴 수 있습니다. "
        "메뉴명을 다시 확인하거나 추천 메뉴를 먼저 요청해 주세요."
    )


@function_tool
def search_menu(
    context: RestaurantContext,
    dietary_preference: str = "",
    category: str = "",
) -> str:
    """
    Search the menu by dietary preference or category.

    Args:
        dietary_preference: Filter such as vegetarian or gluten-free
        category: starter, main, dessert, or beverage
    """
    results = MENU_ITEMS

    if dietary_preference:
        preference = dietary_preference.strip().lower()
        results = [
            item
            for item in results
            if preference in {tag.lower() for tag in item["tags"]}
        ]

    if category:
        category_name = category.strip().lower()
        results = [
            item for item in results if item["category"].lower() == category_name
        ]

    if not results:
        return "조건에 맞는 메뉴를 찾지 못했습니다. 다른 조건으로 다시 찾아드릴게요."

    lines = [
        f"- {item['name']} ({item['category']}) - {item['price']:,}원"
        for item in results
    ]
    return "추천 가능한 메뉴입니다:\n" + "\n".join(lines)


@function_tool
def get_menu_item_details(context: RestaurantContext, item_name: str) -> str:
    """
    Return ingredients, price, and dietary tags for a specific menu item.

    Args:
        item_name: Menu item name
    """
    item = _find_menu_item(item_name)
    if not item:
        return f"'{item_name}' 메뉴를 찾지 못했습니다."

    tags = ", ".join(item["tags"]) if item["tags"] else "none"
    allergens = ", ".join(item["allergens"]) if item["allergens"] else "none"
    ingredients = ", ".join(item["ingredients"])
    return (
        f"{item['name']} 정보입니다.\n"
        f"- 가격: {item['price']:,}원\n"
        f"- 재료: {ingredients}\n"
        f"- 알레르기 유발 성분: {allergens}\n"
        f"- 특징: {tags}"
    )


@function_tool
def check_allergen_info(context: RestaurantContext, item_name: str) -> str:
    """
    Return allergen information for a menu item.

    Args:
        item_name: Menu item name
    """
    item = _find_menu_item(item_name)
    if not item:
        return f"'{item_name}' 메뉴를 찾지 못했습니다."

    allergens = item["allergens"]
    if not allergens:
        return f"{item['name']}에는 등록된 주요 알레르기 유발 성분이 없습니다."

    return f"{item['name']} 알레르기 정보: {', '.join(allergens)}"


@function_tool
def place_order(
    context: RestaurantContext,
    items: str,
    service_type: str = "매장",
    special_request: str = "",
) -> str:
    """
    Create an order summary from the requested items.

    Args:
        items: Ordered items with quantities
        service_type: 매장, 포장, or 배달
        special_request: Extra request for the kitchen
    """
    validation_message = _menu_validation_message(items)
    if validation_message:
        return validation_message

    note = special_request if special_request else "없음"
    return (
        "주문 접수를 시작했습니다.\n"
        f"- 주문 메뉴: {items}\n"
        f"- 이용 방식: {service_type}\n"
        f"- 요청사항: {note}\n"
        "최종 확인을 원하시면 confirm_order 도구로 확인해 주세요."
    )


@function_tool
def confirm_order(
    context: RestaurantContext,
    items: str,
    service_type: str = "매장",
    special_request: str = "",
) -> str:
    """
    Confirm the order for the guest.

    Args:
        items: Ordered items with quantities
        service_type: 매장, 포장, or 배달
        special_request: Extra request for the kitchen
    """
    validation_message = _menu_validation_message(items)
    if validation_message:
        return validation_message

    note = special_request if special_request else "없음"
    return (
        "주문이 확인되었습니다.\n"
        f"- 주문 메뉴: {items}\n"
        f"- 이용 방식: {service_type}\n"
        f"- 요청사항: {note}\n"
        "추가 수정이 필요하면 바로 말씀해 주세요."
    )


@function_tool
def check_reservation_availability(
    context: RestaurantContext,
    date: str,
    time: str,
    party_size: int,
) -> str:
    """
    Check whether a reservation slot is likely available.

    Args:
        date: Reservation date
        time: Reservation time
        party_size: Number of guests
    """
    if party_size > 8:
        return (
            f"{date} {time}에는 {party_size}인 대형 예약은 전화 확인이 필요합니다. "
            f"{context.phone_number}로 연락 주시면 바로 도와드리겠습니다."
        )

    return (
        f"{date} {time}, {party_size}인 예약 가능 좌석을 확인했습니다. "
        "예약 확정을 원하시면 이름과 연락처를 알려주세요."
    )


@function_tool
def create_reservation(
    context: RestaurantContext,
    name: str,
    phone: str,
    date: str,
    time: str,
    party_size: int,
) -> str:
    """
    Create a reservation confirmation message.

    Args:
        name: Guest name
        phone: Guest phone number
        date: Reservation date
        time: Reservation time
        party_size: Number of guests
    """
    return (
        "예약이 접수되었습니다.\n"
        f"- 예약자명: {name}\n"
        f"- 연락처: {phone}\n"
        f"- 일시: {date} {time}\n"
        f"- 인원: {party_size}명\n"
        f"- 매장: {context.restaurant_name} {context.branch_name}"
    )


@function_tool
def offer_refund_resolution(context: RestaurantContext, issue_summary: str) -> str:
    """
    Record a refund review request for a complaint.

    Args:
        issue_summary: Brief summary of the guest's complaint
    """
    return (
        "불편을 드려 죄송합니다. 환불 검토 요청을 접수했습니다.\n"
        f"- 내용: {issue_summary}\n"
        f"- 매장: {context.restaurant_name} {context.branch_name}\n"
        "담당자가 확인 후 가능한 가장 빠르게 안내드리겠습니다."
    )


@function_tool
def offer_discount_resolution(
    context: RestaurantContext,
    issue_summary: str,
    discount_percent: int = 50,
) -> str:
    """
    Offer a service recovery discount for a future visit.

    Args:
        issue_summary: Brief summary of the guest's complaint
        discount_percent: Discount percentage for the next visit
    """
    return (
        "불편을 드려 죄송합니다. 서비스 회복 차원에서 다음 방문 시 사용할 수 있는 "
        f"{discount_percent}% 할인 안내를 준비했습니다.\n"
        f"- 내용: {issue_summary}\n"
        "원하시면 사용 방법까지 이어서 안내드리겠습니다."
    )


@function_tool
def request_manager_callback(
    context: RestaurantContext,
    issue_summary: str,
    customer_name: str = "",
    phone: str = "",
) -> str:
    """
    Request a direct callback from the restaurant manager.

    Args:
        issue_summary: Brief summary of the guest's complaint
        customer_name: Guest name when available
        phone: Callback number when available
    """
    name = customer_name if customer_name else "미확인"
    callback_number = phone if phone else "미확인"
    return (
        "매니저 직접 연락 요청을 접수했습니다.\n"
        f"- 내용: {issue_summary}\n"
        f"- 고객명: {name}\n"
        f"- 연락처: {callback_number}\n"
        f"- 대표번호: {context.phone_number}\n"
        "연락처가 아직 없으면 회신 가능한 번호를 알려주세요."
    )


@function_tool
def escalate_serious_complaint(
    context: RestaurantContext,
    issue_summary: str,
    severity: str = "high",
) -> str:
    """
    Escalate a serious complaint for urgent human follow-up.

    Args:
        issue_summary: Brief summary of the guest's complaint
        severity: low, medium, high, or urgent
    """
    return (
        "중요 민원으로 분류해 즉시 에스컬레이션했습니다.\n"
        f"- 심각도: {severity}\n"
        f"- 내용: {issue_summary}\n"
        f"- 긴급 연락처: {context.phone_number}\n"
        "안전, 위생, 차별, 반복적인 서비스 실패 문제는 매니저가 우선 확인합니다."
    )


class AgentToolUsageLoggingHooks(AgentHooks):
    async def on_tool_start(
        self,
        context: RunContextWrapper[RestaurantContext],
        agent: Agent[RestaurantContext],
        tool: Tool,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** starting tool: `{tool.name}`")

    async def on_tool_end(
        self,
        context: RunContextWrapper[RestaurantContext],
        agent: Agent[RestaurantContext],
        tool: Tool,
        result: str,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** used tool: `{tool.name}`")
            st.code(result)

    async def on_handoff(
        self,
        context: RunContextWrapper[RestaurantContext],
        agent: Agent[RestaurantContext],
        source: Agent[RestaurantContext],
    ):
        with st.sidebar:
            st.write(f"🔄 Handoff: **{source.name}** → **{agent.name}**")

    async def on_start(
        self,
        context: RunContextWrapper[RestaurantContext],
        agent: Agent[RestaurantContext],
    ):
        with st.sidebar:
            st.write(f"🚀 **{agent.name}** activated")

    async def on_end(
        self,
        context: RunContextWrapper[RestaurantContext],
        agent: Agent[RestaurantContext],
        output,
    ):
        with st.sidebar:
            st.write(f"🏁 **{agent.name}** completed")
