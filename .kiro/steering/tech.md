---
inclusion: always
---

# 기술 스택 및 개발 환경

## 빌드 시스템
- **Primary**: Hatchling (modern Python packaging)
- **Legacy**: setuptools with setup.py (maintained for compatibility)
- **Package Manager**: pip with requirements files
- **Documentation**: Sphinx with ReadTheDocs integration

## Core Dependencies
- **Python**: 3.7+ (officially supports 3.9+)
- **HTTP**: requests, httpx, aiohttp for various HTTP client needs
- **Async**: asyncio, aiometer for asynchronous operations
- **CLI**: argparse, inquirerpy for command-line interfaces
- **Output**: rich, pygments, pyfiglet for enhanced console output
- **Blockchain**: eth_keyfile, coincurve for wallet operations (optional)
- **Cloud**: boto3, aioboto3 for AWS integration (optional)

## Development Tools
- **Testing**: unittest, parameterized
- **Linting**: ruff for code formatting and linting
- **Type Checking**: mypy, pyright for static analysis
- **Documentation**: sphinx, myst-parser, furo theme

## Common Commands

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.dev.txt

# Install with optional features
pip install pawnlib[wallet]  # Blockchain wallet support
pip install pawnlib[full]    # All optional dependencies
```

### Building & Testing
```bash
# Run tests
make test
python -m unittest tests/test_*.py

# Build package
make build          # Standard build
make full_build     # Build with all dependencies

# Clean build artifacts
make clean
```

### Local Development
```bash
# Install locally for testing
make local

# Deploy to test server
make local_deploy
```

### Documentation
```bash
# Generate documentation
make gendocs
make pandoc  # Convert README to RST
```

### Docker Operations
```bash
# Build Docker image
make docker

# Run interactive container
make bash

# Push to registry
make push_hub
```

## 핵심 아키텍처 패턴
- **믹스인 클래스**: `LoggerMixin`, `LoggerMixinVerbose`를 통한 일관된 로깅
- **글로벌 설정**: `pawnlib_config` 싱글톤으로 애플리케이션 설정 관리
- **모듈형 CLI**: 서브 명령어 기반의 모듈형 CLI 설계
- **듀얼 API**: 동기/비동기 인터페이스 동시 제공
- **Rich 통합**: Rich 라이브러리를 통한 향상된 콘솔 출력

## 개발 도구 사용법
- **테스트**: `make test` 또는 `python -m unittest` 사용
- **빌드**: `make build` (표준) 또는 `make full_build` (전체 의존성)
- **로컬 설치**: `make local`로 개발 환경 설치
- **문서 생성**: `make gendocs`로 Sphinx 문서 빌드
- **Docker**: `make docker`로 컨테이너 이미지 빌드

## 의존성 관리
- 선택적 기능은 extras로 관리: `pip install pawnlib[wallet]`, `pip install pawnlib[full]`
- 개발 의존성: `requirements.dev.txt` 사용
- 프로덕션 의존성: `requirements.txt` 및 `pyproject.toml` 관리