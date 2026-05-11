# Backend 작업 가이드

## 역할
FastAPI 기반 API 서버. 시뮬 세션 관리, 제어 입력 주입, WebSocket 스트리밍, 예측 API를 담당한다.

## 포함 내용
- `app/api/` — REST/WebSocket 엔드포인트
- `app/services/` — 비즈니스 로직 (`session_service`, `forecast_service`, `threshold_service`)
- `app/domain/` — 도메인 모델 + IGCC 태그 매핑 (`tags.py` — 제어 10개)
- `app/repositories/` — DB 접근 레이어 (**현재 비어있음 — sensor/threshold repo 폐기됨**)
- `app/adapters/` — 외부 시스템 어댑터
  - `simulator/` — 실시간 시뮬 어댑터 (구 `predictor`에서 개명)
  - `forecaster/` — 5분 horizon NOx 예측 어댑터 (신설)
- `app/db/` — DB 연결, 세션 (**ORM 모델 모두 폐기 — `db/models/__init__.py` 빈 상태**)
- `app/schemas/` — Pydantic 요청/응답 스키마
- `app/core/`, `config.py` — 공통 유틸, 설정 (`syngas_lhv` 등)
- `tests/` — pytest 테스트 (29개)

기술 스택: FastAPI, Pydantic, SQLAlchemy, asyncio

## 현재 스펙 (PR #35/#36/#38)
- **ControlVars 10개** — `app/domain/tags.py`의 `_FIELD_RULES`가 SoT
- **OutputVars** — nox/exhaust_temp/power/lambda_/efficiency (5개, `co` 제외)
- **Simulator vs Forecaster 분리** — DI 슬롯 별도 (`app/core/lifespan.py`)
- **Forecast horizon 5분 고정** — `target_minutes` 필드 제거 (`schemas/prediction.py`)
- **efficiency 후처리** — `power/(syngas_flow × syngas_lhv)`를 `sim_loop`에서 계산
- **운영 임계 SoT** — `digital_twin/simulation/config.py::ThresholdConfig` 직결, `GET /api/threshold` 9개 필드 반환
- **sensor 엔드포인트 폐기** — 운영 데이터 조회 페이지 미구현

## ⛔ 금지 사항
- 시뮬 세션 상태를 DB에 직접 저장 — in-memory State Store만 사용 (초기 버전)
- DT 모델을 직접 import해서 호출 — `app/adapters/`를 통한 호출만 허용
- API 응답 스키마를 임의 변경 — 프론트와 협의 (`[API 임시]`)
- DB 컬럼명을 추측해서 사용 — DB 팀 협의 후 (`[DB 협의 필요]`)
- `co` 필드를 schema/응답에 부활시키기 — 학습 타겟에서 제외됨
- ControlVars 필드를 10개 외로 변경 — `tags.py::_FIELD_RULES`와 `digital_twin/simulation/state.py::ControlVars`를 동시 갱신해야 함
- `threshold_config` ORM/repo 재도입 — DT config 직결을 우회하지 말 것
- `prediction_service`로 명명 복귀 — `forecast_service`가 현행 (5분 horizon 명시)
- Simulator와 Forecaster를 단일 어댑터로 통합 — DI 슬롯 분리 유지

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
