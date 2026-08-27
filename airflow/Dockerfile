FROM apache/airflow:3.3.1-python3.12

ARG OPENLINEAGE_SPARK_VERSION=1.52.0
ARG OPENLINEAGE_SCALA_VERSION=2.13

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    jar_name="openlineage-spark_${OPENLINEAGE_SCALA_VERSION}-${OPENLINEAGE_SPARK_VERSION}.jar"; \
    base_url="https://repo1.maven.org/maven2/io/openlineage/openlineage-spark_${OPENLINEAGE_SCALA_VERSION}/${OPENLINEAGE_SPARK_VERSION}"; \
    mkdir -p /opt/airflow/jars; \
    curl -fsSL "${base_url}/${jar_name}" -o "/opt/airflow/jars/${jar_name}"; \
    expected="$(curl -fsSL "${base_url}/${jar_name}.sha512")"; \
    echo "${expected}  /opt/airflow/jars/${jar_name}" | sha512sum -c -; \
    chmod 0444 "/opt/airflow/jars/${jar_name}"

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_OPENLINEAGE_JAR=/opt/airflow/jars/openlineage-spark_2.13-1.52.0.jar

USER airflow
COPY requirements.txt /tmp/datamind-airflow-requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==3.3.1" \
    -r /tmp/datamind-airflow-requirements.txt
