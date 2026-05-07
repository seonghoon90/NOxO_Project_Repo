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

## EC2 수동 배포 확인

EC2에서는 백엔드 컨테이너가 같은 Docker 네트워크의 PostgreSQL 컨테이너를 바라보도록 `docker-compose.ec2.yml`을 함께 적용합니다.

```bash
docker compose --profile local-db --env-file .env \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  -f docker/docker-compose.ec2.yml \
  up -d --build
```

컨테이너 상태 확인:

```bash
docker compose --profile local-db --env-file .env \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  -f docker/docker-compose.ec2.yml \
  ps
```

## Jenkins CD Credential 설정

`Jenkinsfile`의 EC2 배포 stage는 Git에 pem 키나 Slack Webhook을 저장하지 않습니다.
아래 값은 Jenkins UI의 Credentials에만 등록합니다.

| Credential ID | Kind | 용도 |
| --- | --- | --- |
| `ec2-team1-ssh-key` | SSH Username with private key | Jenkins가 EC2에 SSH 접속할 때 사용하는 pem 키 |
| `slack-webhook-url` | Secret text | CI/CD 성공 또는 실패 결과를 Slack으로 알림 |

`ec2-team1-ssh-key` 생성 시 username은 `ubuntu`로 입력하고, private key에는 pem 파일 내용을 붙여 넣습니다.

## dev 브랜치 자동 배포 흐름

Jenkins job이 `dev` 브랜치의 `Jenkinsfile`을 실행하면 아래 순서로 진행됩니다.

```text
Compose Config
Build Test Images
Backend Tests
Frontend Build
Deploy to EC2
Slack Notification
```

배포 stage는 EC2 서버의 `/home/ubuntu/NOxO_Project_Repo`에서 최신 `dev`를 pull한 뒤 운영용 compose 조합으로 컨테이너를 재기동합니다.

```bash
docker compose --profile local-db --env-file .env \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  -f docker/docker-compose.ec2.yml \
  up -d --build
```
