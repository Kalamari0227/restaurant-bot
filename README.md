# Restaurant Bot

OpenAI Agents SDK의 `handoff` 기능으로 동작하는 간단한 레스토랑 멀티 에이전트 챗봇입니다.

구성:
- `Triage Agent`: 사용자 의도를 분류하고 적절한 전문가에게 handoff
- `Menu Agent`: 메뉴, 재료, 채식 옵션, 알레르기 질문 처리
- `Order Agent`: 주문 접수 및 확인
- `Reservation Agent`: 예약 가능 여부 확인 및 예약 접수
- `Complaints Agent`: 음식/서비스 불만을 공감하며 처리하고 보상 또는 에스컬레이션 제안
- `Input Guardrails`: 레스토랑과 무관한 질문과 부적절한 언어 차단
- `Output Guardrails`: 정중하지 않거나 내부 정보를 드러내는 응답 차단

실행:

```bash
uv sync
uv run streamlit run main.py
```

UI에서는 handoff가 일어날 때 `메뉴 전문가에게 연결합니다...` 같은 안내 문구가 채팅 영역에 표시됩니다.
불만 메시지는 `Complaints Agent`로 handoff되며, 심각한 민원은 매니저 콜백 또는 즉시 에스컬레이션 흐름으로 처리됩니다.
