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
        CI_ENV_FILE = 'docker/.env.ci'
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
SLACK_WEBHOOK_URL=
'''
                )
            }
        }

        stage('Compose Config') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_DATA} config --quiet'
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} config --quiet'
            }
        }

        stage('Build Test Images') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} build backend frontend'
            }
        }

        stage('Backend Tests') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} run --rm --no-deps backend pytest -c apps/backend/pytest.ini apps/backend/tests'
            }
        }

        stage('Frontend Build') {
            steps {
                sh 'docker compose --env-file ${CI_ENV_FILE} -f ${COMPOSE_FRONT_BACK} build frontend'
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
    }
}
