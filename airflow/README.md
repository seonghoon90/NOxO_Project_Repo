# Airflow ETL 운영 가이드

NOxO 프로젝트의 원천 CSV 적재 파이프라인을 Airflow DAG로 실행합니다.

## 실행

```bash
docker compose --env-file .env -f docker/docker-compose.data.yml up -d postgres airflow
```

Airflow UI는 `http://localhost:8080`에서 확인합니다. `airflow standalone` 모드의 초기 관리자 계정은 컨테이너 로그에 출력됩니다.

```bash
docker logs noxo_airflow
```

## DAG

- DAG ID: `noxo_sensor_data_etl`
- 주요 흐름: CSV 파일 확인 -> PostgreSQL 연결 확인 -> ETL 실행 및 검증 -> Slack 성공 알림
- 실패 시: 실패한 task와 에러 메시지를 Slack으로 전송

## 환경변수

실제 Slack Webhook URL은 Git에 커밋하지 않고 `.env`의 `SLACK_WEBHOOK_URL`에만 저장합니다.

로컬 PC에서 직접 ETL을 실행할 때는 `DATABASE_URL`의 host가 `localhost`입니다. Airflow 컨테이너 안에서는 Docker Compose 네트워크를 사용하므로 `docker/docker-compose.data.yml`에서 host를 `postgres`로 주입합니다.
