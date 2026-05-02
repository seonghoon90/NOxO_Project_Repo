# Frontend 작업 가이드

## 역할
React + Vite 기반 운영자 대시보드. 공장 도면, 제어 패널, Trend Plot, 멀티 변수 모니터링 UI를 제공한다.

## 포함 내용
- `src/app/` — App.tsx, router.tsx (앱 진입점, 라우팅)
- `src/pages/` — 화면 단위 컴포넌트 (Service, About, Database, Team, DigitalTwin)
- `src/features/dashboard/` — 대시보드 핵심 기능 (mockConsole 등)
- `src/assets/` — 이미지, 정적 자원
- `src/index.css`, `main.tsx` — 글로벌 스타일, 엔트리

기술 스택: React, TypeScript, Vite

## ⛔ 금지 사항
- 백엔드 API 스키마를 추측해서 호출 — `docs/BACKEND_PRD.md` 또는 `[API 임시]` 협의 후 반영
- WebSocket 연결을 페이지 단위로 직접 생성 — features 레이어에서 관리
- 타입 정의를 `any`로 회피 — 명확한 타입 또는 schema 기반 타입 생성
- 변수명을 PRD/Architecture 문서와 다르게 임의 변경 (예: flame_temp ↔ exhaust_temp)

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
