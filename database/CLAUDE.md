# Database 작업 가이드

## 역할
PostgreSQL 스키마 정의, 데이터 적재 스크립트, ERD 관리.

## 포함 내용
- `db_definition.md` — 스키마 정의 문서 (현재 v1.1, **v1.2 갱신 대기 중**)
- `ERD.png` — ERD 다이어그램 (PR #35~#38 반영 갱신 대기 중)
- `load_to_postgres.py` — 데이터 적재 스크립트 (`COLUMN_MAPPING` 14컬럼으로 확장 대기 중)
- `requirements.txt` — DB 관련 Python 의존성

기술 스택: PostgreSQL, psycopg2/SQLAlchemy

## 진행 중 변경 (PR #35/#36/#37/#38 반영)
- 운영 컬럼 표준: 제어 10 + 출력 4 (총 14컬럼) — 도메인 식별자와 일치
- 컬럼 개명: `igv`→`igv_opening`, `dgan_offset`→`n2_offset`, `dgan_flow`→`n2_flow`, `generator_output`→`power_mw`
- 신규 컬럼 7개: `n2_valve_1`, `syngas_srv`, `syngas_gcv_1`, `syngas_gcv_1a`, `syngas_gcv_2`, `ibh_valve`, `exhaust_temp`
- `threshold_config` 테이블 폐기 예정 — 임계값 SoT는 `digital_twin/simulation/config.py`
- 상세 내역: [`docs/DB_CHANGE_REQUEST.md`](../docs/DB_CHANGE_REQUEST.md)

## ⛔ 금지 사항
- 스키마/컬럼명 임의 변경 — DB 팀 협의 필수 (`[DB 협의 필요]`)
- production DB에 직접 쓰기 — 적재 스크립트는 staging부터 검증
- 인증 정보를 코드/스크립트에 하드코딩 — `.env` 사용
- ERD와 실제 스키마 불일치 방치 — 변경 시 ERD 동시 갱신
- `threshold_config` 테이블 재도입 — 임계 SoT는 코드(`digital_twin/simulation/config.py::ThresholdConfig`)이며 DB 동기화는 금지
- `co` (CO 농도) 컬럼 추가 — 학습 타겟에서 제외됨 (`docs/REFACTOR_FLAME_TEMP_TO_EXHAUST_TEMP.md`)
- 컬럼명을 도메인 식별자(`digital_twin/simulation/state.py::ControlVars`)와 다르게 명명

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
