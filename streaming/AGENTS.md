# Streaming 작업 가이드

Kafka(Redpanda) 기반 실시간 센서 스트리밍의 토픽 컨벤션과 적재 멱등성을 지킨다 — bootstrap 누락·offset reset 오설정·중복 적재가 가장 큰 위험.

**Tradeoff**: 실시간 적재용 `sensor_data_stream` 테이블을 batch ETL의 `sensor_data`와 분리하면 단일 테이블 단순함을 포기하는 대신 두 적재 경로의 충돌과 데이터 오염을 차단한다.

## 1. WHAT — 이 모듈은 무엇을 하는가

IGCC 가스터빈 운전 데이터(`NOx_test_20250825.csv`)를 1초 간격으로 Kafka에 발행하고, 별도 consumer가 PostgreSQL `sensor_data_stream` 테이블에 적재하는 실시간 시뮬레이션 파이프라인. backend의 ML 모드 입력 또는 대시보드 실시간 시연용.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `producer.py` — CSV → Kafka 발행 (`KafkaProducer`)
  - 기본 토픽 `noxo.sensor.raw`, 부트스트랩 `localhost:19092`
  - bootstrap 분(`KAFKA_BOOTSTRAP_MINUTES`, 기본 15) 이후 행부터 발행
- `etl_consumer.py` — Kafka → PostgreSQL 적재
  - 대상 테이블 `sensor_data_stream` (DDL: `database/sensor_data_stream.sql`)
  - consumer group `noxo-stream-etl`
- `sensor_csv.py` — 입력 CSV 파서 + `iter_sensor_rows_after_bootstrap`, `load_bootstrap_rows`
- `Dockerfile` — producer/consumer 공용 이미지
- `requirements.txt` — `kafka-python`, `python-dotenv`, `sqlalchemy`, `psycopg`
- `__init__.py` — 패키지 진입점

기술 스택: kafka-python 2.0, SQLAlchemy 2.0, psycopg 3.2, Redpanda(Kafka 호환)

주요 환경변수: `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_SENSOR_TOPIC`, `KAFKA_INPUT_FILE`, `KAFKA_PRODUCE_INTERVAL_SECONDS`, `KAFKA_MAX_MESSAGES`, `KAFKA_BOOTSTRAP_MINUTES`, `KAFKA_ETL_CONSUMER_GROUP_ID`, `STREAM_ETL_DATABASE_URL`, `STREAM_ETL_POSTGRES_HOST`, `STREAM_ETL_POSTGRES_PORT`, `DATABASE_URL`.

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **새 토픽/메시지 스키마**: `producer.py`의 `value_serializer` 입력 dict 키를 변경하면 `etl_consumer.py`의 row 매핑도 동시 갱신. JSON 평면 구조 유지.
- **새 입력 CSV**: `sensor_csv.py::DEFAULT_INPUT_FILE` 또는 `KAFKA_INPUT_FILE` 환경변수로 전환. 컬럼 헤더 변경 시 `parse_value` 호환성 점검.
- **새 적재 컬럼**: `database/sensor_data_stream.sql` 수정 → `etl_consumer.py`의 INSERT 컬럼 동기화 → [`database/AGENTS.md`](../database/AGENTS.md) 영향 평가.
- **로컬 검증**: `docker compose -f docker/docker-compose.kafka.yml up -d`로 Redpanda + producer + etl-consumer 일괄 기동.
- **자동 루프**: `producer.py`의 `run_producer_loop`는 CSV 소진 시 처음(15분 이후)부터 재발행. `KAFKA_MAX_MESSAGES=0`(기본)이면 무한, `> 0`이면 N개 후 종료.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- bootstrap 단계 없이 producer 기동 — `iter_sensor_rows_after_bootstrap`이 부트스트랩 분 이후 행만 발행하도록 설계됨. 우회 시 consumer가 학습 구간 행까지 적재해 운영 데이터 오염
- consumer group을 즉석에서 변경한 채 production 재기동 — offset 재설정 시 중복 적재 또는 누락. 변경 시 토픽 lag 확인 후
- `auto_offset_reset`을 `earliest`로 임의 전환 — 토픽 전체 재처리 → 중복 적재. 변경은 의도된 backfill 시에만
- producer 실행 환경에서 CSV 파일이 컨테이너 내부에 없음 — `KAFKA_INPUT_FILE` 또는 `data/raw/` 볼륨 마운트 확인 (기본 경로는 `data/raw/250811-250825/NOx_test_20250825.csv`)
- `sensor_data_stream`을 batch ETL 대상(`sensor_data`)으로 오인해 적재 — 두 테이블은 의도적으로 분리. 혼합 시 schema/적재 정책 충돌
- secrets(`DATABASE_URL` 등)를 코드/compose 평문 — `.env` 또는 Airflow Connections 사용
- producer를 stateless 단발 스크립트로 가정해 외부 supervisor로 재기동 시도 — 자체 무한 루프이므로 외부 재기동은 컨테이너 stop/start로만 의미가 있음 (`/api/reset` 경로)

## 5. WHERE — 다른 모듈과의 의존성

- **의존**:
  - [`database/AGENTS.md`](../database/AGENTS.md): `sensor_data_stream` 테이블(`database/sensor_data_stream.sql` DDL)
  - [`docker/AGENTS.md`](../docker/AGENTS.md): `docker-compose.kafka.yml`로 Redpanda + producer + consumer 기동
- **피의존**:
  - [`apps/backend/AGENTS.md`](../apps/backend/AGENTS.md): `app/core/kafka_stream.py`가 동일 토픽 소비 (실시간 시뮬 모드 입력)
- **경계 / 어댑터**:
  - 토픽: `noxo.sensor.raw` (JSON 평면 구조)
  - 입력 CSV → producer → Kafka → etl_consumer → PostgreSQL `sensor_data_stream`

## 6. WHY — 코드에 안 적힌 배경 지식

- **bootstrap 분 개념**: 모델 학습/시연 시작점을 맞추기 위해 CSV의 앞 15분(`KAFKA_BOOTSTRAP_MINUTES`) 데이터는 발행 대상에서 제외. 학습 구간과 운영 구간 경계를 producer가 직접 보장.
- **`sensor_data` vs `sensor_data_stream` 분리**: batch ETL(Airflow)의 `sensor_data`는 학습/조회용 정제 데이터, streaming의 `sensor_data_stream`은 실시간 시뮬용 raw. 두 경로의 적재 정책/스키마가 달라 분리.
- **Redpanda 채택 이유**: Kafka 호환 + JVM 불요로 로컬/EC2 리소스 절약. 운영 동작은 동일.
- **사건 이력**: stream ETL의 `auto_offset_reset` 기본값이 잘못 설정돼 재기동마다 전체 토픽을 재적재하던 이슈가 PR #54에서 수정됨.
- **producer 자동 루프 도입 배경**: 시연 데이터가 하루치 CSV 1개뿐이라, 단발 발행으로는 23시간 45분 이후 데이터 흐름이 끊긴다. 시각상 "이음매"(CSV 끝→처음 점프)는 시연 데이터 특성상 허용.

## 7. COMMANDS — 빌드/테스트/린트

- 전체 스택 기동: `docker compose -f docker/docker-compose.kafka.yml up -d`
- 단독 producer 실행: `python -m streaming.producer`
- 단독 consumer 실행: `python -m streaming.etl_consumer`
- 토픽 확인: `docker compose -f docker/docker-compose.kafka.yml exec redpanda rpk topic list`

**영역 고유 명령어 가드**:
- producer를 `KAFKA_MAX_MESSAGES=0`(기본)로 production에 띄우면 CSV 종료까지 무한 발행 — 의도된 시연이 아니면 명시적 상한 설정
- `rpk topic delete` 등 파괴적 명령을 production에서 실행 — consumer lag/offset 영구 손실
- consumer를 production 환경에서 DB 접속 설정 없이 기동 — `STREAM_ETL_DATABASE_URL` 또는 `POSTGRES_*`/`STREAM_ETL_POSTGRES_*` 조합 누락 시 적재 무한 실패 + lag 폭증
- EC2 Docker 내부 consumer에 host용 `DATABASE_URL`을 그대로 주입 — `host.docker.internal` 이름 해석 실패. 같은 compose network의 DB는 `STREAM_ETL_POSTGRES_HOST=postgres`를 사용

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

<!-- `learn` 스킬(`/learn` 또는 Codex의 `$learn`)로 누적되는 영역. -->

_(아직 없음)_
