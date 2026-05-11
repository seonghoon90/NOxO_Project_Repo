# Frontend 작업 가이드

## 역할
React + Vite 기반 운영자 대시보드. 공장 도면, 제어 패널, Trend Plot, 멀티 변수 모니터링 UI를 제공한다.

## 포함 내용
- `src/app/` — App.tsx, router.tsx (앱 진입점, 라우팅)
- `src/pages/` — 화면 단위 컴포넌트 (Service, About, Database, Team, DigitalTwin)
- `src/features/dashboard/` — 대시보드 핵심 기능
  - `HmiSchematic/` — SVG 기반 공정 도면 (14 KPI, 빌드 파이프라인 자동 산출)
  - `useThresholds.ts` — `GET /api/threshold` 마운트 시 1회 호출 (임계 단일 진실원 hook)
  - `mockConsole.ts`, `useConsoleState.ts` — 시뮬/예측 모드 상태 관리
- `src/assets/` — 이미지, 정적 자원
- `src/index.css`, `main.tsx` — 글로벌 스타일, 엔트리
- `scripts/buildHmiSvg/` — SVG 정제 + `schematic-roles.ts` 자동 산출 (npm script)

기술 스택: React, TypeScript, Vite, vitest

## 현재 스펙 (PR #38)
- **ControlPayload 10필드** — `sendControl`이 모든 필드 전송 (기존 3개 → 422 발생)
- **표시값** — 발전량(MW)이 아닌 **발전 효율** 우선 (KPI/sidebar/테이블), 도면 KPI는 MW 유지
- **임계 SoT** — `useThresholds` hook (`GET /api/threshold`), 화면 내 하드코딩 금지
- **예측 모드** — 1Hz `POST /api/prediction` 폴링 → `predictedNox` 갱신, sidebar 컨트롤 잠금
- **CO 시계열 제거** — 학습 타겟에서 제외 + 백엔드 미전송
- **MetricPoint 누적 필드** — efficiency 포함 (60s 변동폭 표시용)
- **HMI 도면** — 수기 HmiMonitor.tsx 폐기, `HmiSchematic` 진입 컴포넌트 + svgr inline 사용

## ⛔ 금지 사항
- 백엔드 API 스키마를 추측해서 호출 — `docs/BACKEND_PRD.md` 또는 `[API 임시]` 협의 후 반영
- WebSocket 연결을 페이지 단위로 직접 생성 — features 레이어에서 관리
- 타입 정의를 `any`로 회피 — 명확한 타입 또는 schema 기반 타입 생성
- 변수명을 PRD/Architecture 문서와 다르게 임의 변경 (예: flame_temp ↔ exhaust_temp)
- 임계값을 컴포넌트/페이지에 하드코딩 — `useThresholds` hook을 통해서만 접근
- `co` 시계열/카드/테이블 행 부활 — 백엔드 미전송 + 학습 타겟 제외
- ControlPayload에 10필드 외 임의 키 추가/제거 — 백엔드 `ControlPayload`와 1:1 동기화 필수
- 수기 SVG 편집 — `scripts/buildHmiSvg`로 자동 산출, `schematic-roles.ts`/`schematic.svg`는 산출물

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
