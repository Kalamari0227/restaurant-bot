# Restaurant Bot

OpenAI Agents SDK의 `handoff` 기능으로 동작하는 간단한 레스토랑 멀티 에이전트 챗봇입니다.

구성:
- `Triage Agent`: 사용자 의도를 분류하고 적절한 전문가에게 handoff
- `Menu Agent`: 메뉴, 재료, 채식 옵션, 알레르기 질문 처리
- `Order Agent`: 주문 접수 및 확인
- `Reservation Agent`: 예약 가능 여부 확인 및 예약 접수

실행:

```bash
uv sync
uv run streamlit run main.py
```

UI에서는 handoff가 일어날 때 `메뉴 전문가에게 연결합니다...` 같은 안내 문구가 채팅 영역에 표시됩니다.
