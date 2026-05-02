# Airflow 작업 가이드

## 역할
데이터 파이프라인 DAG 정의 및 운영.

## 포함 내용
- `dags/` — DAG 정의 파일
- `README.md` — Airflow 운영 안내

기술 스택: Apache Airflow

## ⛔ 금지 사항
- DAG에 secrets 하드코딩 — Airflow Variables 또는 환경변수 사용
- production DB에 직접 쓰기 — staging 거쳐서 검증
- 단일 task에 과도한 책임 부여 — 작업 단위별로 task 분리
- DAG 스케줄을 사전 검토 없이 production에 배포

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
