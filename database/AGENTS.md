# Database 작업 가이드

production DB와 schema 정합성을 지킨다 — 컬럼명은 `digital_twin/simulation/state.py::ControlVars`와 1:1 매핑되며 DB 팀 협의 없이 변경 금지.

**Tradeoff**: 컬럼명을 도메인 식별자에 묶고 임계 SoT를 코드로 옮기면 DB 단독 진화 자유와 DBA의 SQL 즉시 조정 편의를 포기하는 대신 어댑터 매핑 폭증을 차단하고 임계 변경 이력을 git에 남긴다.

## 1. WHAT — 이 모듈은 무엇을 하는가

PostgreSQL 스키마 정의 및 운영 데이터 적재. IGCC 가스터빈 운전 센서 데이터의 14개 운영 컬럼을 `sensor_data` 테이블에 저장하며, ERD와 컬럼 정의서를 코드와 동기 유지한다.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `db_definition.md` — 스키마 정의 문서 (v1.2 — 14컬럼 운영 표준)
- `ERD.png` — ERD 다이어그램 (PR #35~#38 반영)
- `load_to_postgres.py` — 데이터 적재 스크립트 (`COLUMN_MAPPING` 14컬럼)
- `requirements.txt` — DB 관련 Python 의존성

기술 스택: PostgreSQL, psycopg2/SQLAlchemy

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **컬럼 추가/변경**: `db_definition.md` 갱신 → `ERD.png` 동시 갱신 → `load_to_postgres.py::COLUMN_MAPPING` 동기화 → backend `app/db/`, `app/schemas/`, digital_twin `simulation/state.py::ControlVars` 영향 평가.
- **변경 요청 절차**: 상세 내역은 [`docs/DB_CHANGE_REQUEST.md`](../docs/DB_CHANGE_REQUEST.md)에 기록한 뒤 진행.
- **마이그레이션**: staging DB에서 검증 → production 적용. alembic 또는 수기 SQL.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- 스키마/컬럼명 임의 변경 — DB 팀 협의 필수 (`[DB 협의 필요]`). 컬럼명은 코드 도메인 식별자(`digital_twin/simulation/state.py::ControlVars`)와 1:1
- ERD와 실제 스키마 불일치 방치 — 변경 시 `ERD.png`와 `db_definition.md` 동시 갱신 (체크리스트)
- `threshold_config` 테이블 재도입 — 임계 SoT는 코드(`digital_twin/simulation/config.py::ThresholdConfig`), DB 동기화는 폐기됨
- `co` (CO 농도) 컬럼 추가 — 학습 타겟에서 제외됨 (`docs/REFACTOR_FLAME_TEMP_TO_EXHAUST_TEMP.md`)
- 컬럼명을 도메인 식별자와 다르게 명명 — backend/digital_twin과 불일치 시 어댑터 매핑 코드 폭증

## 5. WHERE — 다른 모듈과의 의존성

- **의존**: 외부 IGCC 가스터빈 센서 CSV (`data/**`, git 제외)
- **피의존**:
  - [`apps/backend/AGENTS.md`](../apps/backend/AGENTS.md): `app/db/`, `app/schemas/`가 14컬럼 schema 참조
  - [`digital_twin/AGENTS.md`](../digital_twin/AGENTS.md): 컬럼명을 `ControlVars`/`OutputVars` 식별자와 동기
  - [`airflow/AGENTS.md`](../airflow/AGENTS.md): `noxo_sensor_etl_dag.py`가 `sensor_data` 적재
- **경계 / 어댑터**:
  - `load_to_postgres.py::COLUMN_MAPPING` — CSV TagName → DB 컬럼명 변환

## 6. WHY — 코드에 안 적힌 배경 지식

- **현재 스펙 (PR #35/#36/#37/#38 누적)**:
  - 운영 컬럼 표준: 제어 10 + 출력 4 (총 14컬럼) — 도메인 식별자와 일치
  - 컬럼 개명 이력: `igv`→`igv_opening`, `dgan_offset`→`n2_offset`, `dgan_flow`→`n2_flow`, `generator_output`→`power_mw`
  - 신규 컬럼 7개: `n2_valve_1`, `syngas_srv`, `syngas_gcv_1`, `syngas_gcv_1a`, `syngas_gcv_2`, `ibh_valve`, `exhaust_temp`
  - `threshold_config` 테이블 폐기 — 임계값 SoT는 `digital_twin/simulation/config.py`
  - 상세 내역: [`docs/DB_CHANGE_REQUEST.md`](../docs/DB_CHANGE_REQUEST.md)
- **데이터셋 운용**: 2025-08-11 ~ 2025-08-25 (학습용 14일 + 시뮬용 1일). 원본 CSV는 git 제외 (용량/보안), 로컬·EC2에 직접 복사 또는 S3 다운로드.
- **wide-format CSV**: 원본은 `TagName` 컬럼이 측정 시각 역할. `load_to_postgres.py`가 long-format으로 변환 후 적재.

## 7. COMMANDS — 빌드/테스트/린트

- 적재 (staging): `python database/load_to_postgres.py` <!-- .env에 DB_URL=staging 설정 후 -->
- 스키마 확인: `psql $DATABASE_URL -c "\d sensor_data"`
- ERD 갱신: 외부 도구 (dbdiagram.io 등)로 재생성 후 `ERD.png` 갱신

**영역 고유 명령어 가드**:
- `DROP TABLE`/`TRUNCATE` 등 파괴적 명령을 production에서 실행 — 백업 + DB 팀 승인 필수 (production 직쓰기 금지는 root 공통 가드)

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

<!-- `learn` 스킬(`/learn` 또는 Codex의 `$learn`)로 누적되는 영역. -->

_(아직 없음)_
