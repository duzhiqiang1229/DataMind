FROM apache/airflow:3.3.1-python3.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow
COPY requirements.txt /tmp/datamind-airflow-requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.1" \
    -r /tmp/datamind-airflow-requirements.txt
