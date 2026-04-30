import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib import request

from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(os.getenv("NOXO_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.load_to_postgres import DEFAULT_TARGET_FOLDER, get_database_url, run_pipeline


load_dotenv(PROJECT_ROOT / ".env")


def send_slack_message(text: str) -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[Slack] SLACK_WEBHOOK_URL이 없어 알림을 건너뜁니다.")
        return

    payload = json.dumps({"text": text}).encode("utf-8")
    slack_request = request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(slack_request, timeout=10) as response:
        print(f"[Slack] 알림 전송 완료. status={response.status}")


def notify_failure(context: dict) -> None:
    task = context.get("task_instance")
    dag_id = context.get("dag").dag_id if context.get("dag") else "unknown"
    exception = context.get("exception")
    send_slack_message(
        "[NOxO ETL 실패]\n"
        f"- dag: {dag_id}\n"
        f"- task: {task.task_id if task else 'unknown'}\n"
        f"- error: {exception}"
    )


def check_raw_csv_files() -> dict:
    file_list = sorted(DEFAULT_TARGET_FOLDER.glob("*.csv"))
    if not file_list:
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {DEFAULT_TARGET_FOLDER}")

    result = {
        "file_count": len(file_list),
        "folder": str(DEFAULT_TARGET_FOLDER),
    }
    print(f"[Check] CSV 파일 {result['file_count']}개 확인: {result['folder']}")
    return result


def check_postgres_connection() -> str:
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
    print(f"[Check] PostgreSQL 연결 확인: {db_name}")
    return db_name


def run_sensor_etl() -> dict:
    result = run_pipeline()
    return {
        "row_count": result["row_count"],
        "start_at": str(result["start_at"]),
        "end_at": str(result["end_at"]),
        "null_row_count": result["null_row_count"],
    }


def notify_success(**context) -> None:
    result = context["ti"].xcom_pull(task_ids="run_sensor_etl")
    send_slack_message(
        "[NOxO ETL 성공]\n"
        "- table: public.sensor_data\n"
        f"- rows: {result['row_count']:,}\n"
        f"- period: {result['start_at']} ~ {result['end_at']}\n"
        f"- null rows: {result['null_row_count']}"
    )


default_args = {
    "owner": "noxo-data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=3),
    "on_failure_callback": notify_failure,
}


with DAG(
    dag_id="noxo_sensor_data_etl",
    description="IGCC 센서 CSV를 PostgreSQL에 적재하고 Slack으로 결과를 알립니다.",
    default_args=default_args,
    start_date=datetime(2025, 8, 11),
    schedule=None,
    catchup=False,
    tags=["noxo", "etl", "postgres", "slack"],
) as dag:
    check_raw_csv = PythonOperator(
        task_id="check_raw_csv_files",
        python_callable=check_raw_csv_files,
    )

    check_postgres = PythonOperator(
        task_id="check_postgres_connection",
        python_callable=check_postgres_connection,
    )

    run_etl = PythonOperator(
        task_id="run_sensor_etl",
        python_callable=run_sensor_etl,
    )

    send_success = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
    )

    [check_raw_csv, check_postgres] >> run_etl >> send_success
