# Airflow 작업 가이드

production 데이터 파이프라인의 멱등성과 자격 증명 안전을 지킨다 — DAG 직접 secrets 노출·sub-DAG 미검토 배포·전체 backfill이 가장 큰 위험.

**Tradeoff**: staging→production 단계 검증을 강제하면 hotfix 속도를 포기하는 대신 ETL 버그의 운영 데이터 오염을 차단한다.

## 1. WHAT — 이 모듈은 무엇을 하는가

데이터 파이프라인 DAG 정의 및 운영. 현재는 IGCC 가스터빈 센서 데이터를 `sensor_data` 테이블로 batch ETL 하는 단일 DAG(`noxo_sensor_etl_dag.py`)를 운영한다. 실시간 스트리밍은 별도(`streaming/`).

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `dags/noxo_sensor_etl_dag.py` — 센서 데이터 batch ETL DAG (145줄, `database.load_to_postgres` 직접 import해 호출)
- `README.md` — Airflow 운영 안내

기술 스택: Apache Airflow + SQLAlchemy(검증용) + python-dotenv

DAG 환경변수: `NOXO_PROJECT_ROOT`(repo 루트 경로), `SLACK_WEBHOOK_URL`(실패 알림, optional). 기타 DB 연결은 `.env`/Airflow Connections.

배포 관련: [`docs/data-platform/airflow-operationalization.md`](../docs/data-platform/airflow-operationalization.md)

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **새 DAG**: `dags/<name>_dag.py` 추가. 단일 task 책임 분리, 의존 관계는 `>>`로 명시.
- **스케줄 변경**: `schedule_interval` 변경 시 staging DAG에서 검증 → production 반영.
- **외부 연결**: DB/Kafka 등 연결 정보는 Airflow Connections 또는 `.env`. DAG 모듈은 `dotenv.load_dotenv`로 repo 루트 `.env`를 읽는다.
- **database 모듈 호출**: 현행 DAG는 `from database.load_to_postgres import run_pipeline` 형태로 직접 import (PROJECT_ROOT를 `sys.path`에 추가). 변경 시 [`database/AGENTS.md`](../database/AGENTS.md) 영향 평가.
- **테스트**: `airflow dags test <dag_id> <execution_date>`로 local backfill.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- 단일 task에 과도한 책임 부여 — 작업 단위별로 task 분리 (실패 시 재시도 단위가 너무 큼)
- DAG 스케줄을 사전 검토 없이 production에 배포 — 잘못된 cron이 무한 backfill 유발
- 같은 `dag_id`를 다른 파일에서 중복 정의 — Airflow가 한쪽만 로드, 의도와 다른 DAG 실행 위험
- `database.load_to_postgres`의 함수 시그니처를 DAG 합의 없이 변경 — DAG가 직접 import하므로 즉시 깨짐. 변경 시 양쪽 PR 동시
- `SLACK_WEBHOOK_URL` 미설정 상태에서 production 운영 — 실패 알림 누락. optional이지만 prod에서는 필수

## 5. WHERE — 다른 모듈과의 의존성

- **의존**:
  - [`database/AGENTS.md`](../database/AGENTS.md): `sensor_data` 적재 대상 (14컬럼) + `load_to_postgres.run_pipeline` 직접 호출 (모듈 강결합)
  - [`docker/AGENTS.md`](../docker/AGENTS.md): `docker-compose.airflow.ec2.yml`로 배포
- **피의존**: 운영 데이터 소비자 전반 (backend, frontend, analysis, streaming의 etl_consumer는 별도 경로)
- **경계 / 어댑터**: 외부 소스(CSV/S3) → `database.load_to_postgres` 호출로 `sensor_data` 적재

## 6. WHY — 코드에 안 적힌 배경 지식

- **EC2 배포**: `docker-compose.airflow.ec2.yml`로 운영. 상세는 [`docs/data-platform/airflow-operationalization.md`](../docs/data-platform/airflow-operationalization.md).
- **batch vs 실시간 분리**: Airflow는 batch ETL 전담(주기 적재). Kafka 기반 실시간 스트리밍은 [`streaming/AGENTS.md`](../streaming/AGENTS.md) (`producer.py`/`etl_consumer.py`). 두 경로의 대상 테이블이 다름 (`sensor_data` vs `sensor_data_stream`).
- **DAG가 database 모듈을 직접 import하는 이유**: 별도 어댑터를 두지 않고 함수 호출 결합을 택해 단일 DAG의 응집도를 우선. 신규 DAG가 추가되어 결합이 부담되면 어댑터 도입 재검토.

## 7. COMMANDS — 빌드/테스트/린트

- DAG 로컬 테스트: `airflow dags test noxo_sensor_etl_dag $(date -u +%Y-%m-%d)`
- DAG 목록: `airflow dags list`
- Docker Compose 기동: `docker compose -f docker/docker-compose.airflow.ec2.yml up -d` ([`docker/AGENTS.md`](../docker/AGENTS.md))

**영역 고유 명령어 가드**:
- `airflow dags backfill` 실행 시 범위 지정 누락 — 전체 기간 backfill 폭주 위험
- production scheduler를 일시 정지 없이 DAG 코드 hot-reload — 진행 중 task가 inconsistent state로 종료될 수 있음

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

<!-- `learn` 스킬(`/learn` 또는 Codex의 `$learn`)로 누적되는 영역. -->

_(아직 없음)_
