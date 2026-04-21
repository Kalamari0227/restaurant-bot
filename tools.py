import streamlit as st
from agents import Agent, AgentHooks, RunContextWrapper, Tool, function_tool

from models import RestaurantContext


MENU_ITEMS = [
    {
        "name": "Truffle Mushroom Risotto",
        "category": "main",
        "price": 23000,
        "ingredients": ["arborio rice", "mushroom", "truffle oil", "parmesan"],
        "allergens": ["dairy"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Garden Pasta",
        "category": "main",
        "price": 19000,
        "ingredients": ["pasta", "tomato", "zucchini", "olive", "basil"],
        "allergens": ["gluten"],
        "tags": ["vegetarian"],
    },
    {
        "name": "Chicken Teriyaki Bowl",
        "category": "main",
        "price": 18000,
        "ingredients": ["chicken", "rice", "soy sauce", "sesame"],
        "allergens": ["soy", "sesame"],
        "tags": [],
    },
    {
        "name": "Shrimp Rose Pasta",
        "category": "main",
        "price": 21000,
        "ingredients": ["shrimp", "cream", "pasta", "tomato"],
        "allergens": ["shellfish", "dairy", "gluten"],
        "tags": [],
    },
    {
        "name": "Citrus Salad",
        "category": "starter",
        "price": 12000,
        "ingredients": ["lettuce", "orange", "walnut", "vinaigrette"],
        "allergens": ["tree nuts"],
        "tags": ["vegetarian", "gluten-free"],
    },
    {
        "name": "Chocolate Lava Cake",
        "category": "dessert",
        "price": 9000,
        "ingredients": ["chocolate", "egg", "flour", "butter"],
        "allergens": ["egg", "gluten", "dairy"],
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
