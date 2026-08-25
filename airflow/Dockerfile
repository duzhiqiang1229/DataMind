FROM apache/airflow:3.3.1-python3.12

COPY requirements.txt /tmp/datamind-airflow-requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.1" \
    -r /tmp/datamind-airflow-requirements.txt
