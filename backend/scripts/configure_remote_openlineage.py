"""Configure OpenLineage on the remote business Airflow/Spark host.

Run this from the DataMind backend container. The script loads the existing
Airflow SSH settings from DataMind's encrypted component configuration and
routes events through the authenticated relay, so no secret is accepted on
the command line or copied to the Airflow host.
"""

import asyncio
import json
import os
import shlex
import time
from pathlib import PurePosixPath
from urllib.parse import urlparse

import paramiko

from app.core.database import async_session
from app.services.airflow_service import _airflow_ssh_config


AIRFLOW_VERSION = "2.10.5"
OPENLINEAGE_PROVIDER_VERSION = "2.8.0"
SPARK_PROVIDER_VERSION = "5.3.4"
SPARK_AGENT_VERSION = "1.39.0"
OPENLINEAGE_CLIENT_VERSION = "1.39.0"
PIPELINE_SERVICE = "datamind_airflow"


def validate_endpoint(value: str) -> str:
    value = value.rstrip("/") + "/"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OPENLINEAGE_OM_URL must be an absolute HTTP(S) URL")
    expected_suffix = "/api/v1/openlineage/"
    if not parsed.path.endswith(expected_suffix):
        raise ValueError(f"OPENLINEAGE_OM_URL must end with {expected_suffix}")
    return value


def run(client: paramiko.SSHClient, command: str, timeout: int = 600) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    if output:
        print(output, end="", flush=True)
    if error:
        print(error, end="", flush=True)
    if exit_code:
        raise RuntimeError(f"remote command failed ({exit_code}): {command.splitlines()[0]}")
    return output


def ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    current = PurePosixPath("/")
    for part in PurePosixPath(path).parts[1:]:
        current /= part
        try:
            sftp.stat(str(current))
        except FileNotFoundError:
            sftp.mkdir(str(current))


def write_remote(
    sftp: paramiko.SFTPClient, path: str, content: str, mode: int = 0o644
) -> None:
    ensure_remote_dir(sftp, str(PurePosixPath(path).parent))
    temp_path = f"{path}.tmp"
    with sftp.open(temp_path, "w") as handle:
        handle.write(content)
        handle.flush()
    sftp.chmod(temp_path, mode)
    try:
        sftp.remove(path)
    except FileNotFoundError:
        pass
    sftp.rename(temp_path, path)


async def load_config() -> dict:
    async with async_session() as db:
        ssh = await _airflow_ssh_config(db)
    return ssh


async def main() -> None:
    endpoint = validate_endpoint(
        os.environ.get(
            "OPENLINEAGE_OM_URL",
            "http://127.0.0.1:18585/api/v1/openlineage/",
        )
    )
    ssh = await load_config()
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh["host"], port=ssh["port"], username=ssh["user"],
        password=ssh["password"], timeout=15,
    )
    try:
        print("[1/6] Checking OpenMetadata reachability from business Airflow", flush=True)
        health_url = endpoint.split("/api/v1/openlineage/", 1)[0] + "/api/v1/system/version"
        run(client, f"curl -fsS --connect-timeout 10 {shlex.quote(health_url)} >/dev/null")

        print("[2/6] Backing up the Python and service configuration", flush=True)
        backup_dir = f"/home/airflow/openlineage-backups/{timestamp}"
        run(client, " && ".join([
            f"mkdir -p {shlex.quote(backup_dir)}",
            f"/home/airflow/venv/bin/pip freeze > {shlex.quote(backup_dir + '/pip-freeze.txt')}",
            f"cp -a /etc/systemd/system/airflow-scheduler.service {shlex.quote(backup_dir + '/airflow-scheduler.service')}",
            f"cp -a /etc/systemd/system/airflow-webserver.service {shlex.quote(backup_dir + '/airflow-webserver.service')}",
            f"test ! -f /home/spark/conf/spark-defaults.conf || cp -a /home/spark/conf/spark-defaults.conf {shlex.quote(backup_dir + '/spark-defaults.conf')}",
            f"test ! -f /home/airflow/dags/etl_dim_dwd.py || cp -a /home/airflow/dags/etl_dim_dwd.py {shlex.quote(backup_dir + '/etl_dim_dwd.py')}",
        ]))

        print("[3/6] Installing compatible Airflow OpenLineage providers", flush=True)
        run(client, " ".join([
            "/home/airflow/venv/bin/pip install --disable-pip-version-check --timeout 60 --index-url https://pypi.org/simple --only-binary=openlineage-sql",
            shlex.quote(f"apache-airflow=={AIRFLOW_VERSION}"),
            shlex.quote(f"apache-airflow-providers-openlineage=={OPENLINEAGE_PROVIDER_VERSION}"),
            shlex.quote(f"apache-airflow-providers-apache-spark=={SPARK_PROVIDER_VERSION}"),
            shlex.quote(f"openlineage-python=={OPENLINEAGE_CLIENT_VERSION}"),
            shlex.quote(f"openlineage-integration-common=={OPENLINEAGE_CLIENT_VERSION}"),
            shlex.quote(f"openlineage-sql=={OPENLINEAGE_CLIENT_VERSION}"),
        ]), timeout=1200)

        print("[4/6] Installing the Spark OpenLineage listener", flush=True)
        jar_name = f"openlineage-spark_2.12-{SPARK_AGENT_VERSION}.jar"
        jar_path = f"/home/spark/jars/{jar_name}"
        jar_url = (
            "https://repo1.maven.org/maven2/io/openlineage/"
            f"openlineage-spark_2.12/{SPARK_AGENT_VERSION}/{jar_name}"
        )
        run(client,
            f"if ! test -s {shlex.quote(jar_path)}; then "
            f"curl -fL --retry 3 --connect-timeout 20 {shlex.quote(jar_url)} "
            f"-o {shlex.quote(jar_path + '.tmp')} && "
            f"mv {shlex.quote(jar_path + '.tmp')} {shlex.quote(jar_path)}; fi",
            timeout=600,
        )

        transport = json.dumps({
            "type": "http", "url": endpoint, "endpoint": "lineage",
        }, separators=(",", ":"))
        env_content = "\n".join([
            f"AIRFLOW__OPENLINEAGE__NAMESPACE={PIPELINE_SERVICE}",
            f"AIRFLOW__OPENLINEAGE__TRANSPORT='{transport}'",
            "AIRFLOW__OPENLINEAGE__SPARK_INJECT_PARENT_JOB_INFO=true",
            # Keep transport injection off: SparkSubmitOperator logs its full
            # command, which would otherwise expose the bot JWT in task logs.
            "AIRFLOW__OPENLINEAGE__SPARK_INJECT_TRANSPORT_INFO=false",
            "",
        ])
        print("[5/6] Writing protected runtime configuration", flush=True)
        with client.open_sftp() as sftp:
            write_remote(sftp, "/etc/airflow/openlineage.env", env_content, 0o600)
            service_commands = {
                "airflow-scheduler": "/home/airflow/venv/bin/airflow scheduler",
                "airflow-webserver": "/home/airflow/venv/bin/airflow webserver -p 8082",
            }
            for service, command in service_commands.items():
                wrapper_path = f"/usr/local/sbin/{service}-openlineage"
                wrapper = (
                    "#!/bin/bash\nset -a\n"
                    ". /etc/airflow/openlineage.env\n"
                    f"exec {command}\n"
                )
                write_remote(sftp, wrapper_path, wrapper, 0o755)
                dropin = (
                    "[Service]\n"
                    "EnvironmentFile=/etc/airflow/openlineage.env\n"
                    "ExecStart=\n"
                    f"ExecStart={wrapper_path}\n"
                )
                write_remote(sftp,
                    f"/etc/systemd/system/{service}.service.d/openlineage.conf", dropin)
            try:
                with sftp.open("/home/spark/conf/spark-defaults.conf", "r") as handle:
                    spark_defaults = handle.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                spark_defaults = ""
            kept = [line for line in spark_defaults.splitlines()
                    if not line.strip().startswith("spark.openlineage.")
                    and not line.strip().startswith("spark.extraListeners")]
            kept.extend([
                "", "# OpenLineage automatic table-level lineage",
                "spark.extraListeners io.openlineage.spark.agent.OpenLineageSparkListener",
                f"spark.openlineage.namespace {PIPELINE_SERVICE}", "",
                "spark.openlineage.transport.type http",
                "spark.openlineage.transport.url http://127.0.0.1:18585",
                "spark.openlineage.transport.endpoint api/v1/openlineage/lineage",
                "spark.openlineage.transport.timeoutInMillis 5000",
                "",
            ])
            write_remote(
                sftp, "/home/spark/conf/spark-defaults.conf", "\n".join(kept), 0o600
            )

            # Spark --verbose prints every default property, including the
            # transport credential. Disable it in the only retained DAG.
            dag_path = "/home/airflow/dags/etl_dim_dwd.py"
            try:
                with sftp.open(dag_path, "r") as handle:
                    dag_source = handle.read().decode("utf-8", errors="replace")
                safe_source = dag_source.replace("verbose=True", "verbose=False")
                if safe_source != dag_source:
                    write_remote(sftp, dag_path, safe_source)
            except FileNotFoundError:
                pass

        print("[6/6] Restarting and validating Airflow", flush=True)
        run(client,
            "systemctl daemon-reload && "
            "systemctl restart airflow-webserver.service airflow-scheduler.service && "
            "systemctl is-active airflow-webserver.service airflow-scheduler.service",
            timeout=180,
        )
        run(client,
            "/home/airflow/venv/bin/python - <<'PY'\n"
            "from importlib.metadata import version\n"
            "from inspect import signature\n"
            "from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator\n"
            "print('airflow=' + version('apache-airflow'))\n"
            "print('openlineage_provider=' + version('apache-airflow-providers-openlineage'))\n"
            "print('spark_provider=' + version('apache-airflow-providers-apache-spark'))\n"
            "params = signature(SparkSubmitOperator.__init__).parameters\n"
            "print('spark_parent_injection_supported=' + str('openlineage_inject_parent_job_info' in params))\n"
            "print('spark_transport_injection_supported=' + str('openlineage_inject_transport_info' in params))\n"
            "PY\n"
            "set -a; . /etc/airflow/openlineage.env; "
            "/home/airflow/venv/bin/airflow config get-value openlineage namespace")
        print(f"backup={backup_dir}", flush=True)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
