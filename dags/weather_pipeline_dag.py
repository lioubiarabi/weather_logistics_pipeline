from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'start_date': datetime(2026, 9, 19),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'weather_logistics_pipeline',
    default_args=default_args,
    description='Automated Daily Weather Data Extraction and Loading',
    schedule_interval='0 9 * * *',
    catchup=False
) as dag:

    fetch_data = BashOperator(
        task_id='fetch_bronze_layer',
        bash_command='python /opt/airflow/src/extraction/fetch_weather.py'
    )

    clean_data = BashOperator(
        task_id='clean_silver_layer',
        bash_command='python /opt/airflow/src/transformation/clean_data.py'
    )

    build_features = BashOperator(
        task_id='build_gold_layer',
        bash_command='python /opt/airflow/src/transformation/build_features.py'
    )

    load_data = BashOperator(
        task_id='load_postgres',
        bash_command='python /opt/airflow/src/load/load_to_pg.py'
    )

    fetch_data >> clean_data >> build_features >> load_data