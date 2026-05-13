# NOxO Project — Claude/Codex/Antigravity/Cursor 작업 지침

API contract와 schema SoT는 backend·digital_twin·database 3축에 분산돼 있다 — 영역 간 컬럼명·schema·임계치는 협의 없이 임의 변경 금지.

**Tradeoff**: 3축 SoT 분산으로 영역별 미세 튜닝 자유를 포기하는 대신 cross-영역 책임 명료화·변경 이력 추적 가능성을 얻는다.

<!--
이 파일은 map 역할이다. 작업 시 해당 영역의 AGENTS.md를 먼저 읽고 진행한다.
CLAUDE.md는 `@./AGENTS.md` 한 줄로 이 파일을 import 한다 (단일 진실 공급원).
root에 모든 가이드를 몰아넣지 않고 영역별로 분리한 이유는 토큰 효율 + 컨텍스트 정확도다.
디렉토리 트리(`ls`로 알 수 있는 정보)는 의도적으로 넣지 않는다. root map은 라우팅에만 집중한다.
-->

## 영역별 가이드

작업 영역에 해당하는 `AGENTS.md`를 먼저 읽고 진행한다.

- **apps/frontend** — UI/대시보드 작업 → [`apps/frontend/AGENTS.md`](apps/frontend/AGENTS.md)
- **apps/backend** — API/시뮬 세션 작업 → [`apps/backend/AGENTS.md`](apps/backend/AGENTS.md)
- **digital_twin** — 시뮬 엔진/모델 작업 → [`digital_twin/AGENTS.md`](digital_twin/AGENTS.md)
- **database** — 스키마/쿼리 → [`database/AGENTS.md`](database/AGENTS.md)
- **streaming** — Kafka 실시간 파이프라인 (producer/consumer) → [`streaming/AGENTS.md`](streaming/AGENTS.md)
- **analysis** — 분석 스크립트/실험/리포트 → [`analysis/AGENTS.md`](analysis/AGENTS.md)
- **airflow** — DAG/batch ETL → [`airflow/AGENTS.md`](airflow/AGENTS.md)
- **docker** — 컨테이너/배포 → [`docker/AGENTS.md`](docker/AGENTS.md)

CI 파이프라인은 root `Jenkinsfile` + [`docs/ci-cd/`](docs/ci-cd/)와 [`docker/AGENTS.md`](docker/AGENTS.md)의 `jenkins-compose.yml`을 함께 참조.

## 영역 가이드의 구조

<!-- 각 영역의 AGENTS.md는 다음 8섹션 템플릿을 따른다. -->

1. **WHAT** — 이 모듈이 무엇을 하는가
2. **CONTENTS** — 디렉토리 맵 + 기술 스택
3. **HOW** — 일반적인 수정은 어떻게 하는가
4. **HOW NOT** — 시스템을 깨뜨리는 비명백한 함정
5. **WHERE** — 다른 모듈과의 의존성 (강결합 `@import` + 약결합 마크다운 링크)
6. **WHY** — 코드에 안 적힌 배경 지식
7. **COMMANDS** — 빌드/테스트/린트 명령어
8. **LEARNED CAUTIONS** — `learn` 스킬로 누적

## Git 컨벤션

모든 커밋/푸시 작업은 [`docs/GIT_CONVENTIONS.md`](docs/GIT_CONVENTIONS.md)를 따른다.

## 공통 명령어 가드 (전역)

<!-- v1.8: 영역 가이드에는 영역 고유 가드만 두고, 공통 가드는 여기에 모은다 (T3 중복 방지). -->

- `--no-verify` 사용 금지 — pre-commit hook 우회로 broken state commit
- `git push --force`를 `main`/`dev` 브랜치에 적용 금지 — 협업자 변경 유실
- `data/**` 하위 raw CSV를 git에 add 금지 — 용량/보안 정책 ([`database/db_definition.md`](database/db_definition.md) §1)
- production DB에 직접 쓰기 금지 — staging 검증 우회로 데이터 유실/이력 단절
- secrets/자격 증명을 코드·compose·DAG에 하드코딩 금지 — `.env`/Connections/Variables 사용

## 주의사항 학습 (learn 스킬)

작업 중 실수가 발견되면 다음 형태로 호출해 해당 영역 AGENTS.md의 "⚠️ LEARNED CAUTIONS" 섹션에 누적한다.

- Claude Code/Cursor/Antigravity: `/learn <메모>` (인자 없이도 호출 가능)
- Codex: `$learn <메모>`

스킬 위치: `.claude/skills/learn/`, `.agents/skills/learn/`, `.agents/workflows/learn.md`

## 가이드 품질 채점 (guide-audit 스킬)

프로젝트 내 모든 가이드를 v1.6 루브릭으로 채점한다 (결과 콘솔 출력).

- Claude Code/Cursor/Antigravity: `/guide-audit`
- Codex: `$guide-audit`
