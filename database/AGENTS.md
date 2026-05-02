# Database 작업 가이드

## 역할
PostgreSQL 스키마 정의, 데이터 적재 스크립트, ERD 관리.

## 포함 내용
- `db_definition.md` — 스키마 정의 문서
- `ERD.png` — ERD 다이어그램
- `load_to_postgres.py` — 데이터 적재 스크립트
- `requirements.txt` — DB 관련 Python 의존성

기술 스택: PostgreSQL, psycopg2/SQLAlchemy

## ⛔ 금지 사항
- 스키마/컬럼명 임의 변경 — DB 팀 협의 필수 (`[DB 협의 필요]`)
- production DB에 직접 쓰기 — 적재 스크립트는 staging부터 검증
- 인증 정보를 코드/스크립트에 하드코딩 — `.env` 사용
- ERD와 실제 스키마 불일치 방치 — 변경 시 ERD 동시 갱신

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
