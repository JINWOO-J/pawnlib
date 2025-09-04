---
inclusion: always
---

# 프로젝트 구조 및 아키텍처 패턴

## 디렉토리 구조
```
pawnlib/
├── pawnlib/           # 메인 패키지 디렉토리
├── examples/          # 사용 예제 및 데모 코드
├── tests/            # 단위 테스트 및 테스트 유틸리티
├── docs/             # Sphinx 문서화
├── logs/             # 애플리케이션 로그 파일
├── data/             # 테스트 데이터 및 설정 파일
└── governance/       # 블록체인 거버넌스 관련 파일
```

## 메인 패키지 구조 (pawnlib/)
```
pawnlib/
├── __init__.py       # 패키지 초기화
├── __version__.py    # 버전 정보
├── __main__.py       # 메인 엔트리포인트
├── asyncio/          # 비동기 작업 유틸리티
├── blockchain/       # 블록체인 관련 도구 (ICON, Goloop)
├── cli/              # CLI 명령어 모듈들
├── config/           # 설정 관리 시스템
├── exceptions/       # 커스텀 예외 및 알림
├── input/            # 사용자 입력 처리
├── metrics/          # 메트릭 및 모니터링
├── models/           # 데이터 모델 및 응답 객체
├── output/           # 출력 포매팅 및 로깅
├── resource/         # 시스템 리소스 모니터링
├── typing/           # 타입 정의 및 변환 유틸리티
└── utils/            # 범용 유틸리티 함수들
```

## CLI 모듈 구조 (pawnlib/cli/)
각 CLI 명령어는 독립적인 모듈로 구성:
- `main_cli.py` - 메인 CLI 엔트리포인트
- `http.py` - HTTP 요청 및 모니터링 도구
- `icon.py` - ICON 블록체인 관련 명령어
- `server.py` - 서버 리소스 확인 도구
- `proxy.py` - 프록시 리플렉터 도구
- `wallet.py` - 지갑 관리 도구
- `websocket.py` - WebSocket 연결 도구

## 예제 구조 (examples/)
기능별로 분류된 예제 코드:
- `color_print/` - 콘솔 출력 및 포매팅 예제
- `http/` - HTTP 클라이언트 사용 예제
- `icon_rpc_test/` - ICON RPC 호출 예제
- `global_config/` - 글로벌 설정 사용 예제
- `logging/` - 로깅 시스템 예제

## 테스트 구조 (tests/)
- 단위 테스트는 `test_*.py` 패턴 사용
- 각 모듈별로 대응하는 테스트 파일 존재
- `common.py` - 테스트 공통 유틸리티

## 설정 파일 패턴
- `.env` - 환경 변수 설정
- `config.ini` - INI 형식 설정 파일
- `config.yaml` - YAML 형식 설정 파일
- `pyproject.toml` - 프로젝트 메타데이터 및 빌드 설정

## 코딩 컨벤션 및 아키텍처 패턴

### 명명 규칙
- **클래스명**: PascalCase (예: `IconRpcHelper`, `NodeStatsMonitor`)
- **함수/변수명**: snake_case (예: `get_network_info`, `block_height`)
- **상수**: UPPER_SNAKE_CASE (예: `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **비동기 클래스**: `Async` 접두사 사용 (예: `AsyncIconRpcHelper`)

### 아키텍처 패턴
- **믹스인 패턴**: 모든 클래스는 `LoggerMixin` 또는 `LoggerMixinVerbose` 상속 권장
- **글로벌 설정**: `pawnlib_config` 싱글톤 패턴 사용
- **듀얼 API**: 동기/비동기 인터페이스 모두 제공
- **Rich 통합**: 모든 출력은 Rich 라이브러리 활용

### 파일 명명 규칙
- 모듈 파일: `snake_case.py`
- 테스트 파일: `test_*.py`
- 예제 파일: `기능명_test.py` 또는 `기능명.py`
- 설정 파일: `config.*` 형식

### 개발 가이드라인
- 새로운 CLI 명령어는 `pawnlib/cli/` 디렉토리에 독립 모듈로 생성
- 모든 유틸리티 함수는 해당 기능별 디렉토리에 배치
- 예제 코드는 `examples/` 디렉토리에 기능별로 분류하여 저장
- 테스트는 각 모듈에 대응하는 `test_*.py` 파일로 작성