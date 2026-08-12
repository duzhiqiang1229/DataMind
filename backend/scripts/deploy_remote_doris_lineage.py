"""Deploy the Doris-aware OpenLineage operator to the business Airflow host."""

import asyncio
import os
import re
import time
from pathlib import PurePosixPath

import paramiko

from app.core.database import async_session
from app.services.airflow_service import _airflow_ssh_config


LOCAL_PLUGIN = os.environ.get(
    "DORIS_OPENLINEAGE_PLUGIN", "/tmp/doris_openlineage_operator.py"
)
REMOTE_PLUGIN = "/home/airflow/dags/doris_openlineage_operator.py"
REMOTE_DAG = "/home/airflow/dags/etl_dim_dwd.py"
VALIDATION_RUN = "manual__openlineage_validation_20260811T032303Z"


def ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    current = PurePosixPath("/")
    for part in PurePosixPath(path).parts[1:]:
        current /= part
        try:
            sftp.stat(str(current))
        except FileNotFoundError:
            sftp.mkdir(str(current))


def read_remote(sftp: paramiko.SFTPClient, path: str) -> str:
    with sftp.open(path, "r") as handle:
        return handle.read().decode("utf-8", errors="strict")


def write_remote(sftp: paramiko.SFTPClient, path: str, content: str) -> None:
    ensure_remote_dir(sftp, str(PurePosixPath(path).parent))
    temp = path + ".tmp"
    with sftp.open(temp, "w") as handle:
        handle.write(content)
        handle.flush()
    sftp.chmod(temp, 0o644)
    try:
        sftp.remove(path)
    except FileNotFoundError:
        pass
    sftp.rename(temp, path)


def patch_dag(source: str) -> str:
    custom_import = (
        "from doris_openlineage_operator import DorisSparkSubmitOperator"
    )
    spark_import = (
        "from airflow.providers.apache.spark.operators.spark_submit "
        "import SparkSubmitOperator"
    )
    if custom_import not in source:
        if spark_import not in source:
            raise RuntimeError("SparkSubmitOperator import was not found in retained DAG")
        source = source.replace(spark_import, custom_import)
    source = re.sub(
        r"(?<!Doris)\bSparkSubmitOperator\(",
        "DorisSparkSubmitOperator(",
        source,
    )
    if re.search(r"(?<!Doris)\bSparkSubmitOperator\(", source):
        raise RuntimeError("not all SparkSubmitOperator declarations were replaced")
    return source


def run(client: paramiko.SSHClient, command: str, timeout: int = 180) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if output:
        print(output, end="")
    if error:
        print(error, end="")
    if code:
        raise RuntimeError(f"remote validation failed with exit code {code}")
    return output


async def main() -> None:
    with open(LOCAL_PLUGIN, encoding="utf-8") as handle:
        plugin_source = handle.read()

    async with async_session() as db:
        ssh = await _airflow_ssh_config(db)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh["host"], port=ssh["port"], username=ssh["user"],
        password=ssh["password"], timeout=15,
    )
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = f"/home/airflow/openlineage-backups/{timestamp}-doris-operator"
    try:
        with client.open_sftp() as sftp:
            dag_source = read_remote(sftp, REMOTE_DAG)
            updated_dag = patch_dag(dag_source)
            ensure_remote_dir(sftp, backup)
            write_remote(sftp, f"{backup}/etl_dim_dwd.py", dag_source)
            try:
                old_plugin = read_remote(sftp, REMOTE_PLUGIN)
                write_remote(sftp, f"{backup}/doris_openlineage_operator.py", old_plugin)
            except FileNotFoundError:
                pass
            write_remote(sftp, REMOTE_PLUGIN, plugin_source)
            write_remote(sftp, REMOTE_DAG, updated_dag)
            legacy_plugin = "/home/airflow/plugins/doris_openlineage_operator.py"
            try:
                legacy_source = read_remote(sftp, legacy_plugin)
                write_remote(sftp, f"{backup}/legacy-doris_openlineage_operator.py", legacy_source)
                sftp.remove(legacy_plugin)
            except FileNotFoundError:
                pass

            ignore_path = "/home/airflow/dags/.airflowignore"
            try:
                ignore_source = read_remote(sftp, ignore_path)
                safe_ignore = ignore_source.replace("*_script.py", r".*_script\.py")
                if safe_ignore != ignore_source:
                    write_remote(sftp, f"{backup}/.airflowignore", ignore_source)
                    write_remote(sftp, ignore_path, safe_ignore)
            except FileNotFoundError:
                pass

            # The relay now adds authorization. Remove legacy Spark-side auth
            # so neither configuration nor future task logs contain the JWT.
            defaults_path = "/home/spark/conf/spark-defaults.conf"
            defaults = read_remote(sftp, defaults_path)
            safe_defaults = "\n".join(
                line for line in defaults.splitlines()
                if not line.strip().startswith("spark.openlineage.transport.auth.")
            ) + "\n"
            if safe_defaults != defaults:
                write_remote(sftp, defaults_path, safe_defaults)

            # Airflow also posts through the authenticated relay, so its host
            # needs no copy of the OpenMetadata bot credential.
            airflow_env = "/etc/airflow/openlineage.env"
            env_source = read_remote(sftp, airflow_env)
            safe_transport = (
                "AIRFLOW__OPENLINEAGE__TRANSPORT="
                "'{\"type\":\"http\",\"url\":"
                "\"http://127.0.0.1:18585/api/v1/openlineage/\","
                "\"endpoint\":\"lineage\"}'"
            )
            env_lines = [
                safe_transport if line.startswith("AIRFLOW__OPENLINEAGE__TRANSPORT=")
                else line
                for line in env_source.splitlines()
            ]
            safe_env = "\n".join(env_lines) + "\n"
            if safe_env != env_source:
                write_remote(sftp, airflow_env, safe_env)

        print("Validating plugin, DAG imports, and extracted Doris datasets")
        run(client, r"""
set -a
. /etc/airflow/openlineage.env
/home/airflow/venv/bin/python - <<'PY'
import glob
from airflow.models import DagBag
from doris_openlineage_operator import extract_doris_identifiers

bag = DagBag(dag_folder='/home/airflow/dags', include_examples=False)
if bag.import_errors:
    raise SystemExit(f'DAG import errors: {bag.import_errors}')
dag = bag.get_dag('etl_dim_to_ads')
custom = [t for t in dag.tasks if t.__class__.__name__ == 'DorisSparkSubmitOperator']
if not custom:
    raise SystemExit('no DorisSparkSubmitOperator tasks found')
found = []
for path in glob.glob('/opt/etljob/etl/**/*.py', recursive=True):
    try:
        source = open(path, encoding='utf-8').read()
        inputs, outputs = extract_doris_identifiers(source)
        if inputs or outputs:
            found.append((path, sorted(inputs), sorted(outputs)))
    except (OSError, SyntaxError, UnicodeError):
        pass
print(f'dag_tasks={len(dag.tasks)} custom_spark_tasks={len(custom)}')
print(f'parsed_jobs={len(found)}')
for path, inputs, outputs in found:
    print(f'{path}: inputs={inputs} outputs={outputs}')
PY
/home/airflow/venv/bin/airflow tasks list etl_dim_to_ads >/dev/null
""")

        # Redact bearer JWTs from the one validation run whose original verbose
        # Spark command was logged before secure relay injection was enabled.
        log_dir = f"/home/airflow/logs/dag_id=etl_dim_to_ads/run_id={VALIDATION_RUN}"
        run(client, f"""
if test -d '{log_dir}'; then
  /home/airflow/venv/bin/python - <<'PY'
from pathlib import Path
import re
root = Path('{log_dir}')
count = 0
pattern = re.compile(rb'Bearer\\s+eyJ[A-Za-z0-9_.-]+')
for path in root.rglob('*'):
    if path.is_file():
        data = path.read_bytes()
        clean, replacements = pattern.subn(b'Bearer [REDACTED]', data)
        if replacements:
            path.write_bytes(clean)
            count += replacements
print(f'redacted_tokens={{count}}')
PY
fi
""")
        print(f"backup={backup}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
