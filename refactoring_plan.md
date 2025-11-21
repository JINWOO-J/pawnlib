# HTTP 유틸리티 리팩토링 계획

## 현재 상황
- `pawnlib/utils/http.py`: 5,753줄의 거대한 파일
- 단일 책임 원칙 위반
- 유지보수성 저하

## 제안된 구조
```
pawnlib/utils/http/
├── __init__.py          # 공통 인터페이스
├── client.py           # HTTP 클라이언트 기본 기능
├── async_client.py     # 비동기 HTTP 클라이언트
├── monitoring.py       # HTTP 모니터링 기능
├── websocket.py        # WebSocket 관련 기능
├── rpc.py             # JSON-RPC 관련 기능
└── utils.py           # HTTP 유틸리티 함수들
```

## 리팩토링 단계
1. 기능별로 모듈 분리
2. 공통 인터페이스 정의
3. 테스트 케이스 업데이트
4. 하위 호환성 유지를 위한 레거시 임포트 지원