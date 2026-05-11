pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        COMPOSE_PROJECT_NAME = 'noxo_ci'
        COMPOSE_FRONT_BACK = 'docker/docker-compose.yml'
        COMPOSE_DATA = 'docker/docker-compose.data.yml'
        COMPOSE_AIRFLOW_EC2 = 'docker/docker-compose.airflow.ec2.yml'
        CI_ENV_FILE = 'docker/.env.ci'
        DEPLOY_HOST = '15.165.247.216'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/NOxO_Project_Repo'
        DEPLOY_BRANCH = 'dev'
    }

    stages {
        stage('Prepare CI Env') {
            steps {
                writeFile(
                    file: env.CI_ENV_FILE,
                    text: '''POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=igcc_db
LOG_LEVEL=info
AIRFLOW_PORT=8080
ETL_CHUNK_SIZE=50000
SLACK_WEBHOOK_URL=
'''
                )
            }
        }

        stage('Compose Config') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_DATA} config --quiet'
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} config --quiet'
                sh 'docker compose --profile local-db --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} -f docker/docker-compose.prod.yml -f docker/docker-compose.ec2.yml -f ${COMPOSE_AIRFLOW_EC2} config --quiet'
            }
        }

        stage('Build Test Images') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} build backend frontend'
            }
        }

        stage('Backend Tests') {
            steps {
                // -m "not integration" : 실제 모델/DB가 필요한 케이스 (`@pytest.mark.integration`)는 CI에서 제외.
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} run --rm --no-deps backend pytest -c apps/backend/pytest.ini -m "not integration" apps/backend/tests'
            }
        }

        stage('Frontend Build') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} build frontend'
            }
        }

        stage('Deploy to EC2') {
            when {
                expression {
                    return env.GIT_BRANCH == 'origin/dev' || env.BRANCH_NAME == 'dev'
                }
            }
            steps {
                sshagent(credentials: ['ec2-team1-ssh-key']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST} "
                            set -e
                            cd ${DEPLOY_PATH}
                            git fetch origin ${DEPLOY_BRANCH}
                            git checkout ${DEPLOY_BRANCH}
                            git pull --ff-only origin ${DEPLOY_BRANCH}
                            docker compose --profile local-db --env-file .env \
                                -f docker/docker-compose.yml \
                                -f docker/docker-compose.prod.yml \
                                -f docker/docker-compose.ec2.yml \
                                -f docker/docker-compose.airflow.ec2.yml \
                                up -d --build
                            docker compose --profile local-db --env-file .env \
                                -f docker/docker-compose.yml \
                                -f docker/docker-compose.prod.yml \
                                -f docker/docker-compose.ec2.yml \
                                -f docker/docker-compose.airflow.ec2.yml \
                                ps
                            curl -fsS --retry 10 --retry-delay 3 --retry-connrefused http://localhost/api/health
                        "
                    '''
                }
            }
        }
    }

    post {
        always {
            sh '''
                docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} down || true
                rm -f ${CI_ENV_FILE}
            '''
        }
        success {
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_WEBHOOK_URL')]) {
                sh '''
                    set +x
                    curl -fsS -X POST -H 'Content-type: application/json' \
                        --data "{\\"text\\":\\"NOxO 배포 성공: ${JOB_NAME} #${BUILD_NUMBER} (${BUILD_URL})\\"}" \
                        "${SLACK_WEBHOOK_URL}" >/dev/null
                '''
            }
        }
        failure {
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_WEBHOOK_URL')]) {
                sh '''
                    set +x
                    curl -fsS -X POST -H 'Content-type: application/json' \
                        --data "{\\"text\\":\\"NOxO CI/CD 실패: ${JOB_NAME} #${BUILD_NUMBER} (${BUILD_URL})\\"}" \
                        "${SLACK_WEBHOOK_URL}" >/dev/null
                '''
            }
        }
    }
}
