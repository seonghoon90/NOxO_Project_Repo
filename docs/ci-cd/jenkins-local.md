# Jenkins 로컬 CI 가이드

EC2 배포 전, 로컬 Docker Jenkins로 CI 파이프라인을 먼저 검증합니다.

## 목표

- Backend `pytest` 자동 실행
- Frontend production build 자동 실행
- Docker Compose 설정 검증
- 다음 단계에서 EC2 배포 stage를 추가할 수 있는 Jenkinsfile 기반 마련

## Jenkins 실행

Airflow가 `8080`을 사용하므로 Jenkins는 `8081`로 실행합니다.

```bash
docker compose -f docker/jenkins-compose.yml up -d --build
```

Jenkins UI:

```text
http://localhost:8081
```

초기 관리자 비밀번호:

```bash
docker exec noxo_jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

## Pipeline 생성

1. Jenkins UI 접속
2. `New Item`
3. `Pipeline` 선택
4. Pipeline definition을 `Pipeline script from SCM`으로 설정
5. Git repository URL 입력
6. Branch는 테스트할 브랜치 입력
7. Script Path는 `Jenkinsfile`

## 로컬 CI 실행 내용

`Jenkinsfile`은 Jenkins 컨테이너에 Python/Node를 직접 설치하지 않고, Docker Compose 서비스 컨테이너를 이용해 테스트를 실행합니다.

```text
Compose Config
Build Test Images
Backend Tests
Frontend Build
```

## 종료

```bash
docker compose -f docker/jenkins-compose.yml down
```

Jenkins 설정과 job 기록까지 지우려면 volume도 함께 삭제합니다.

```bash
docker compose -f docker/jenkins-compose.yml down -v
```
