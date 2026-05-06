# Docker 작업 가이드

## 역할
컨테이너 구성 (개발/프로덕션/데이터).

## 포함 내용
- `docker-compose.yml` — 기본 compose 설정
- `docker-compose.dev.yml` — 개발 환경
- `docker-compose.prod.yml` — 프로덕션 환경
- `docker-compose.data.yml` — 데이터 관련 서비스
- `jenkins-compose.yml` — 로컬 Jenkins CI 테스트 환경
- `README.md` — Docker 운영 안내

기술 스택: Docker, Docker Compose

## ⛔ 금지 사항
- secrets를 compose 파일에 하드코딩 — `.env` 또는 secret 마운트
- prod 설정을 dev 환경에서 임의 사용 — 환경별 compose 파일 분리 유지
- 이미지 태그를 `latest`로 production 사용 — 명시적 버전 태그
- 호스트 포트를 root 권한 포트(<1024)로 임의 노출

## ⚠️ 학습된 주의사항
> `/learn` 명령어로 누적되는 영역.

_(아직 없음)_
