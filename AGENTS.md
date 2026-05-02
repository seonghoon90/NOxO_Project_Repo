# NOxO Project - Claude/Codex 작업 지침

> 이 파일은 **map** 역할을 한다. 작업 시 해당 영역의 CLAUDE.md를 먼저 읽고 진행한다.

## 프로젝트 구조

```
NOxO_Project_Repo/
├── apps/
│   ├── frontend/      # React + Vite 대시보드
│   └── backend/       # FastAPI 서버
├── digital_twin/      # 시뮬 엔진 + ML 모델
├── database/          # PostgreSQL 스키마
├── analysis/          # 데이터 분석/EDA
├── airflow/           # 데이터 파이프라인 (DAG)
├── docker/            # 컨테이너 구성
├── data/              # 데이터셋 저장소 (코드 작업 영역 아님)
├── docs/              # PRD, Architecture, 컨벤션
├── scripts/           # 공통 스크립트 (sync 등)
└── .githooks/         # 공유 git hooks
```

## 영역별 가이드

작업 영역에 해당하는 CLAUDE.md를 먼저 읽고 진행한다.

- **apps/frontend** — UI/대시보드 작업 → [`apps/frontend/CLAUDE.md`](apps/frontend/CLAUDE.md)
- **apps/backend** — API/시뮬 세션 작업 → [`apps/backend/CLAUDE.md`](apps/backend/CLAUDE.md)
- **digital_twin** — 시뮬 엔진/모델 작업 → [`digital_twin/CLAUDE.md`](digital_twin/CLAUDE.md)
- **database** — 스키마/쿼리 → [`database/CLAUDE.md`](database/CLAUDE.md)
- **analysis** — 분석 노트북/리포트 → [`analysis/CLAUDE.md`](analysis/CLAUDE.md)
- **airflow** — DAG/파이프라인 → [`airflow/CLAUDE.md`](airflow/CLAUDE.md)
- **docker** — 컨테이너/배포 → [`docker/CLAUDE.md`](docker/CLAUDE.md)

## Git 컨벤션

모든 커밋/푸시 작업은 [`docs/GIT_CONVENTIONS.md`](docs/GIT_CONVENTIONS.md)를 따른다.

## 주의사항 학습 (`/learn`)

작업 중 실수가 발생하면 `/learn [메모]`로 해당 영역 CLAUDE.md의 "⚠️ 학습된 주의사항" 섹션에 누적한다.
- 인자 없이 호출하면 최근 대화에서 자동 추론
- 인자가 있으면 그 내용을 추가
- 커맨드 정의: `docs/commands/learn.md`
