<div align="center">

# NOxO

**합성가스 발전소 NOx 시뮬레이션 · 5분 후 예측 콘솔**

운영자가 조작 결과를 미리 보고, 5분 뒤 NOx 상승 위험을 사전에 감지하게 합니다.

[![Live Demo](https://img.shields.io/badge/Live_Demo-15.165.247.216-3b82f6?style=for-the-badge)](http://15.165.247.216/)
&nbsp;
![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-stream-231f20?logo=apachekafka&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ed?logo=docker&logoColor=white)

</div>

---

## 1. 프로젝트 소개

IGCC 가스터빈 G1의 NOx 배출은 운영자가 누른 제어 변수에 **즉시 반응하지 않는다**.
변수 조정 → 결과 확인 사이의 수십 초~수 분의 지연이 곧 NOx 초과 사고의 사각지대였다.

NOxO는 이 사각지대를 두 갈래의 시간 축으로 채운다.

- **PAST → NOW**: 운영자의 조작이 만들어내는 NOx 변화를 Stateful 시뮬레이션으로 미리 본다.
- **NOW → +5MIN**: 현재 센서 시계열로부터 5분 뒤 NOx를 Cantera Physics 보강 회귀로 예측한다.

> **Live**: [http://15.165.247.216/](http://15.165.247.216/) — EC2 + Docker compose + nginx + WebSocket 1Hz 스트리밍

---

## 2. 데모

| 메인 콘솔 (HMI) | 5분 후 NOx 예측 |
|---|---|
| 공정 도면 위에 실시간 KPI·트렌드·임계 경고를 오버레이한 SCADA 스타일 콘솔 | 시계 카드·트렌드·임계 비교를 한 화면에 통합 |
| 10개 제어 변수 · 5개 출력 변수 · 0.2 s step · WebSocket 100–500 ms push | 1 Hz 폴링 · warmup latch · 음수 클립 가드 |

세부 콘텐츠는 콘솔 상단 탭에서 확인할 수 있다 — `프로젝트 소개 · DB 구조 · 시뮬레이션 · 팀원 소개`.

---

## 3. 핵심 기능

### 3.1 Stateful 시뮬레이션
한 step 안에서 **물리 기반 모델과 데이터 기반 모델이 동시에** 풀린다.

```
target ─lag(τ)─► current ─ML 회귀─► output_target ─lag(τ)─► output
                       │                                 │
                       └─► Zeldovich ODE ───────► NOx blend (weighted)
```

- **8단계 step**: 제어 lag → λ 계산 → ML 추론 → 배기온도 lag → Zeldovich 적분 → NOx 블렌딩 → 발전량/효율 → 임계 비교
- **4단 상태 분리** `target / current / output_target / output` — 조작 즉시 반응 같은 비현실적 거동을 차단
- **변수별 시간 상수 τ** — 합성가스 1.0 s · IGV 2.0 s · NOx 5.0 s · 발전량 8.5 s · 배기온도 10.0 s

### 3.2 5분 후 NOx 예측
시뮬레이션이 조작의 결과를 보여준다면, 예측은 조작이 없을 때의 자연 추이를 보여준다.
센서 시계열 + Cantera 기반 물리 보강 피처로 회귀한다.

### 3.3 ML 정상상태 모델
- 학습 단위 **1분 집계** (60초 평균) — 1초 단위 학습 시 자기상관 문제로 가짜 성능이 나오던 이슈를 분리
- **Ridge 0.7 + LightGBM 0.3 앙상블** · 246 피처 · 3 타깃 (NOx · TTXM · DWATT)
- Ridge의 외삽 안정성 + LGB의 비선형 미세조정 결합

---

## 4. 시스템 아키텍처

```
┌───────────────┐   WebSocket    ┌────────────────────────┐   adapter   ┌─────────────────┐
│   Frontend    │◄──────────────►│   Backend (FastAPI)    │◄───────────►│  Digital Twin   │
│  React · Vite │   100–500 ms   │  Sim Loop · Sessions   │             │ Zeldovich + ML  │
│   HMI Console │                │  Forecast · Threshold  │             │ Ridge·LGB 앙상블  │
└───────────────┘                └─────────┬──────────────┘             └─────────────────┘
                                           │
                                   ┌───────┴────────┐
                                   ▼                ▼
                           ┌──────────────┐  ┌──────────────┐
                           │ PostgreSQL   │  │    Kafka     │◄── CSV producer
                           │ sensor_data  │  │ ETL consumer │     (재생 시뮬)
                           └──────────────┘  └──────────────┘
                                           ▲
                                   ┌───────┴────────┐
                                   │   Airflow      │  배치 ETL · 학습 데이터 파이프라인
                                   └────────────────┘
```

**경계 설계**
- Backend는 DT를 **adapter 경유**로만 호출 (`MLSimulator` / `MLForecaster` / `SnapshotDataSource`) — 테스트 모킹·prod fallback 정책 분리
- 운영 임계 단일 진실원: `digital_twin/simulation/config.py::ThresholdConfig` → `GET /api/threshold`로만 노출
- 실시간 세션 상태는 in-memory(`InMemoryStateStore`), 영속은 `simulation_log_repo`로 분리
- `/api/reset`는 in-process가 아닌 **컨테이너 재기동** — producer 상태(시각 포인터)까지 같이 되돌리기 위해 docker-socket-proxy 경유

---

## 5. 기술적 의사결정 하이라이트

| 주제 | 결정 | 이유 |
|---|---|---|
| **모델 학습 단위** | 1초 → 1분 집계 전환 | 1초는 자기상관으로 가짜 성능이 나오던 문제를 분리, 1분 집계에서 안정적인 정상상태 회귀 확보 |
| **물리 + 데이터 하이브리드** | Zeldovich ODE × ML 가중합 | ML 단독은 OOD 외삽 취약, 물리식 단독은 미세 거동 누락 |
| **state 4단 분리** | target / current / output_target / output | UI 반응성과 물리적 관성 분리 — 조작 즉시 출력이 점프하는 비현실 차단 |
| **임계 SoT 일원화** | DT `config.py` → backend `/api/threshold`만 노출 | 프론트·백·시뮬 3축 분산 SoT를 단방향으로 평탄화 |
| **docker-socket-proxy** | backend가 docker.sock 직마운트 ❌, proxy 경유 | RO 마운트라도 컨테이너 탈취 = 호스트 점령. blast radius 축소 |
| **Forecast warmup latch** | "값 → 준비 중" 깜빡임 차단 | 새로고침 직후 1초 미만 윈도우에서 stale/empty 전이가 사용자에게 노출되던 이슈 fix |

---

## 6. 기술 스택

| 영역 | 스택 |
|---|---|
| **Frontend** | React 19 · TypeScript · Vite 8 · Vitest · react-router v7 |
| **Backend** | FastAPI 0.115 · Pydantic 2.9 · SQLAlchemy 2.0 · asyncio · pytest |
| **ML / Physics** | scikit-learn · LightGBM · scipy (ODE) · Cantera |
| **Data / Stream** | PostgreSQL 16 · Kafka · Airflow |
| **Infra / DevOps** | Docker Compose · nginx · Jenkins · EC2 · docker-socket-proxy |

---

## 7. 리포지토리 구조

```
NOxO/
├── apps/
│   ├── frontend/        # React HMI 콘솔
│   └── backend/         # FastAPI · 세션 · 시뮬 루프 · WS
├── digital_twin/        # 시뮬 엔진 · ML · Forecaster
├── streaming/           # Kafka producer / ETL consumer
├── database/            # PostgreSQL DDL · ERD · 적재 스크립트
├── airflow/             # 배치 ETL DAG
├── analysis/            # 분석 노트북 · 리포트
├── docker/              # compose (dev/prod/ec2/kafka) · jenkins
└── docs/                # PRD · Architecture · 의사결정 기록
```

각 영역의 `AGENTS.md`에 WHAT / HOW / HOW NOT / WHERE / WHY / COMMANDS / LEARNED CAUTIONS가 정리되어 있다.

---

## 8. 실행 방법

```bash
# Frontend (개발)
cd apps/frontend && npm install && npm run dev      # → http://localhost:5173

# Backend (개발)
cd apps/backend && uvicorn app.main:app --reload    # → http://localhost:8000

# 전체 통합 기동 (DB · Kafka · backend · frontend)
docker compose -f docker/docker-compose.dev.yml up
```

테스트:
```bash
# Frontend
cd apps/frontend && npm test

# Backend
cd apps/backend && pytest

# Digital Twin
pytest digital_twin/tests/
```

---

## 9. 팀

| 이름 | 역할 | GitHub |
|---|---|---|
| **김희태** *(팀장)* | AI/ML Engineering — Ridge·LGB 앙상블, Zeldovich ODE, 5분 NOx 예측 모델 | [@kimheetae0104](https://github.com/kimheetae0104) |
| 신성훈 | Data · DB Engineering — sensor_data 스키마, Kafka 스트림, 학습 데이터 파이프라인 | [@seonghoon90](https://github.com/seonghoon90) |
| 안태현 | Full-stack · Agentic Engineering — React 콘솔, FastAPI 세션, 에이전트 환경 구축 | [@taehyunan-99](https://github.com/taehyunan-99) |
| 지태현 | Data Analytics — 운전 분포 분석, 임계 산정, 모델 성능 검증 | [@Tay-hyyyyn](https://github.com/Tay-hyyyyn) |

---

<div align="center">

**[Live Demo →](http://15.165.247.216/)**

SeSAC × Fininsight · 2026

</div>
