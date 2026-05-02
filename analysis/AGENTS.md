# Analysis 작업 가이드

## 역할
EDA, 모델링 실험, 리포트 작성. production 코드(`digital_twin/`, `apps/`)와는 분리되어 실험 영역으로 운영된다.

## 포함 내용
- `notebooks/` — Jupyter 노트북 (EDA, 실험)
- `reports/` — 분석 리포트
- `Engineering/configs/` — 실험 설정
- `Engineering/experiments/` — 실험 결과
- `Engineering/models/` — 실험용 모델
- `Engineering/scripts/` — 실험 스크립트
- `Engineering/reports/` — 엔지니어링 리포트

기술 스택: Jupyter, pandas, scikit-learn, matplotlib/seaborn

## ⛔ 금지 사항
- 노트북에 raw 데이터 셀 출력 포함 커밋 — 출력 클리어 후 커밋
- 실험 결과를 production 코드(`digital_twin/`, `apps/`)에 직접 반영 — 검증 후 별도 PR로 이관
- 대용량 데이터/모델을 git에 커밋 — `.gitignore` 확인
- raw 데이터 파일을 `analysis/` 폴더에 직접 배치 — `data/raw/` 사용

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
