# Backend 작업 가이드

## 역할
FastAPI 기반 API 서버. 시뮬 세션 관리, 제어 입력 주입, WebSocket 스트리밍, 예측 API를 담당한다.

## 포함 내용
- `app/api/` — REST/WebSocket 엔드포인트
- `app/services/` — 비즈니스 로직 (시뮬 세션, 예측)
- `app/domain/` — 도메인 모델 (SimulationSession, State 등)
- `app/repositories/` — DB 접근 레이어
- `app/adapters/` — 외부 시스템 어댑터 (DT 호출 등)
- `app/db/` — DB 연결, 세션
- `app/schemas/` — Pydantic 요청/응답 스키마
- `app/core/`, `config.py` — 공통 유틸, 설정
- `tests/` — pytest 테스트

기술 스택: FastAPI, Pydantic, SQLAlchemy, asyncio

## ⛔ 금지 사항
- 시뮬 세션 상태를 DB에 직접 저장 — in-memory State Store만 사용 (초기 버전)
- DT 모델을 직접 import해서 호출 — `app/adapters/`를 통한 호출만 허용
- API 응답 스키마를 임의 변경 — 프론트와 협의 (`[API 임시]`)
- DB 컬럼명을 추측해서 사용 — DB 팀 협의 후 (`[DB 협의 필요]`)

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
