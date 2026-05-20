# Frontend 작업 가이드

백엔드 API 컨트랙트와 도메인 변수명(`exhaust_temp` 등) schema drift를 막는다 — 추측·`any`·임의 변경 금지.

**Tradeoff**: hook 단위 API 캡슐화로 한 줄 fetch의 편의를 포기하는 대신 422/500 런타임 실패를 컴파일 타임으로 옮긴다.

## 1. WHAT — 이 모듈은 무엇을 하는가

React + Vite 기반 운영자 대시보드. 공장 도면(HMI), 제어 패널, Trend Plot, 멀티 변수 모니터링 UI. 백엔드 시뮬/예측 API를 호출해 실시간 운전 데이터와 5분 NOx 예측을 시각화한다.

## 2. CONTENTS — 파일/디렉토리와 기술 스택

- `src/app/` — `App.tsx`, `router.tsx` (앱 진입점, 라우팅)
- `src/pages/` — 화면 단위 컴포넌트 (`ServicePage` index 라우트, `AboutPage`, `DatabasePage`, `DigitalTwinPage`, `TeamPage`)
- `src/features/dashboard/` — 대시보드 핵심 기능
  - `HmiSchematic/` — SVG 기반 공정 도면 컴포넌트 (`HmiSchematic.tsx` 진입 + 헬퍼 모듈들 + colocate 테스트)
  - `useThresholds.ts` — `GET /api/threshold` 마운트 시 1회 호출 (임계 단일 진실원 hook, `ServicePage`에서 소비)
  - `mockConsole.ts`, `useConsoleState.ts` — 시뮬/예측 모드 상태 관리
- `src/test/smoke.test.ts` — 글로벌 smoke 테스트
- `scripts/buildHmiSvg.ts` — HMI SVG 빌드 entry (CLI)
- `scripts/buildHmiSvg/` — entry가 호출하는 내부 모듈 (`ROLE_MAP`, `validateRoles`, `transformAst`, `emitRolesTs` 등)
- `scripts/__tests__/` — 빌드 스크립트 테스트
- `vitest.config.ts`, `vite.config.ts`, `eslint.config.js` — 도구 설정
- `Dockerfile`, `nginx.conf` — 컨테이너 빌드 & 정적 서빙

기술 스택: React 19, TypeScript, Vite 8, Vitest 3, ESLint, react-router-dom v7

## 3. HOW — 일반적인 수정은 어떻게 하는가

- **새 화면 추가**: `src/pages/<Name>.tsx` 생성 → `src/app/router.tsx`에 route 등록.
- **새 대시보드 기능**: `src/features/dashboard/<feature>/`에 컴포넌트 + hook 묶음. 페이지는 합성만.
- **API 연동**: hook 단위로 캡슐화 (`useThresholds` 패턴). 백엔드 schema 변경 시 type 정의 동시 갱신.
- **HMI SVG 변경**: `scripts/buildHmiSvg.ts`가 entry. `ROLE_MAP`/`validateRoles` 등 내부 모듈만 수정하고, 산출물(`schematic-roles.ts`, `schematic.svg`)은 수기 편집 금지.
- **테스트**: 기본은 컴포넌트 옆 colocate(`*.test.ts(x)`) — `HmiSchematic/`이 대표 예시. 전역적 smoke만 `src/test/`에. vitest + @testing-library/react.

## 4. ⛔ HOW NOT — 시스템을 깨뜨리는 비명백한 함정

- 백엔드 API 스키마를 추측해서 호출 — `docs/BACKEND_PRD.md` 또는 `[API 임시]` 협의 후 반영해야 422/500 방지
- WebSocket 연결을 페이지 단위로 직접 생성 — features 레이어에서 관리 안 하면 페이지 이동 시 연결 누수
- 타입 정의를 `any`로 회피 — 런타임 에러 추적 불가, schema drift 은닉
- 변수명을 PRD/Architecture 문서와 다르게 임의 변경 (예: `flame_temp` ↔ `exhaust_temp`) — 백엔드/DB와 컨트랙트 깨짐
- 임계값을 컴포넌트/페이지에 하드코딩 — `useThresholds` hook을 통해서만 접근 (SoT는 `digital_twin/simulation/config.py::ThresholdConfig`)
- `co` 시계열/카드/테이블 행 부활 — 백엔드 미전송 + 학습 타겟 영구 제외 (DT `features.compute_co`는 표시용 파생이지 운영 데이터 아님)
- `ControlPayload`에 10필드 외 임의 키 추가/제거 — 백엔드 `ControlPayload`와 1:1 동기화 필수, 한 쪽 누락 시 422
- 수기 SVG 편집 — `scripts/buildHmiSvg.ts`로 자동 산출, 수기 변경분이 다음 빌드에 덮어쓰임

## 5. WHERE — 다른 모듈과의 의존성

<!-- 강결합: backend가 API contract(Pydantic schema, 엔드포인트) SoT. frontend TS 타입을 backend 정의가 결정한다. -->
@../backend/AGENTS.md

- **의존 (약결합)**: [`digital_twin/AGENTS.md`](../../digital_twin/AGENTS.md)의 `ControlVars`/`OutputVars` 정의 (개념적 SoT, 코드 import는 안 함)
- **피의존**: 없음 (브라우저 최종단)
- **경계 / 어댑터**:
  - HTTP/WebSocket 호출: `src/features/dashboard/` 내부 hook
  - HMI 도면 산출 파이프라인: `scripts/buildHmiSvg.ts` ↔ `src/features/dashboard/HmiSchematic/`

## 6. WHY — 코드에 안 적힌 배경 지식

- **현재 frontend 스펙 (PR #35~#57 반영)**:
  - `ControlPayload` 10필드 — `sendControl`이 모든 필드 전송 (기존 3개 → 백엔드 422 발생 이력)
  - 표시값 우선순위 — 발전량(MW)이 아닌 **발전 효율** 우선 (KPI/sidebar/테이블). 도면 KPI는 MW 유지
  - 임계 SoT — `useThresholds` hook (`GET /api/threshold`), 화면 내 하드코딩 금지
  - 예측 모드 — 1Hz `POST /api/prediction` 폴링 → `predictedNox` 갱신, sidebar 컨트롤 잠금
  - `MetricPoint` 누적 필드 — efficiency 포함 (60초 변동폭 표시용)
  - HMI 도면 — 수기 `HmiMonitor.tsx` 폐기됨, `HmiSchematic` 진입 컴포넌트 + svgr inline 사용
- **CO 시계열 제거 배경**: 학습 타겟에서 영구 제외 (자기상관 + 분포 이슈). 백엔드도 미전송.
- **`flame_temp` → `exhaust_temp` 개명**: 화염 온도가 아닌 배기 온도(TTXM)가 운영 SoT라는 도메인 결정.

## 7. COMMANDS — 빌드/테스트/린트

- 개발 서버: `npm run dev`
- 빌드: `npm run build` <!-- tsc -b && vite build -->
- 테스트: `npm test` <!-- vitest run, watch 모드 자동 제외 -->
- 린트: `npm run lint`
- 타입체크: 빌드 시 `tsc -b`로 함께 수행
- HMI SVG 산출: `npm run hmi:build` <!-- tsx scripts/buildHmiSvg.ts -->

**영역 고유 명령어 가드**:
- `npm run test:watch` / `npm run test:ui`는 자동화에서 hang 유발 — CI/스크립트에서는 `npm test`만 사용
- `package-lock.json` 임의 갱신 후 미커밋 상태로 둠 — 다른 작업자 환경 불일치

## 8. ⚠️ LEARNED CAUTIONS — 학습된 주의사항

- **제어 변수 운영 한계(min/max) 동기화**: `src/features/dashboard/mockConsole.ts::variableSeed`에 정의된 한계값은 백엔드의 `apps/backend/app/domain/tags.py::ControlBounds`와 항상 일치해야 한다. 이 값들은 학습 데이터의 실측 분포(median 등)를 반영하고 있으므로, 임의 변경 시 백엔드 검증 로직과의 불일치로 인해 제어 입력이 거부될 수 있다.
