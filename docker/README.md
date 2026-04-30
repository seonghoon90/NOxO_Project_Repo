# Docker 통합 실행 가이드

프론트엔드와 백엔드는 `docker/` Compose로 실행하고, 데이터베이스는 `docker/docker-compose.data.yml`의 공식 PostgreSQL을 사용합니다.

## 실행 순서

루트 공식 DB를 먼저 실행합니다.

```bash
docker compose --env-file .env -f docker/docker-compose.data.yml up -d postgres
```

프론트엔드/백엔드는 루트 `.env` 값을 읽어 공식 DB에 연결합니다.

```bash
docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --build backend frontend
```

접속 URL:

- Frontend: http://localhost:5173
- Backend health check: http://localhost:8000/api/health

## 참고

`docker/docker-compose.yml`의 `postgres` 서비스는 `local-db` 프로필 전용입니다. 공식 DB 대신 임시 DB가 필요할 때만 사용합니다.
