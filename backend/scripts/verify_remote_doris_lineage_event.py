"""Send one source-derived Doris OpenLineage event through the production path."""

import asyncio
import base64

import paramiko

from app.core.database import async_session
from app.services.airflow_service import _airflow_ssh_config


REMOTE_CHECK = r'''
set -a
. /etc/airflow/openlineage.env
/home/airflow/venv/bin/python - <<'PY'
from datetime import datetime, timezone
import json
import urllib.request
import uuid

from airflow.models import DagBag

dag = DagBag('/home/airflow/dags', include_examples=False).get_dag('etl_dim_to_ads')
tasks = [t for t in dag.tasks if t.__class__.__name__ == 'DorisSparkSubmitOperator']
task = next(t for t in tasks if t._doris_lineage().outputs)
lineage = task._doris_lineage()
run_id = str(uuid.uuid4())

def dataset(value):
    return {'namespace': value.namespace, 'name': value.name, 'facets': {}}

base = {
    'eventTime': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'producer': 'https://datamind.local/openlineage/doris-operator/1.0',
    'schemaURL': 'https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent',
    'run': {'runId': run_id, 'facets': {}},
    'job': {
        'namespace': 'datamind_airflow',
        'name': f'etl_dim_to_ads.{task.task_id}',
        'facets': {},
    },
    'inputs': [dataset(item) for item in lineage.inputs],
    'outputs': [dataset(item) for item in lineage.outputs],
}
for state in ('START', 'COMPLETE'):
    event = dict(base, eventType=state)
    request = urllib.request.Request(
        'http://127.0.0.1:18585/api/v1/openlineage/lineage',
        data=json.dumps(event, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise SystemExit(f'OpenLineage returned HTTP {response.status}')
print(f'verified_task={task.task_id}')
print(f'inputs={len(lineage.inputs)} outputs={len(lineage.outputs)}')
PY
'''


async def main() -> None:
    async with async_session() as db:
        ssh = await _airflow_ssh_config(db)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        ssh["host"], port=ssh["port"], username=ssh["user"],
        password=ssh["password"], timeout=15,
    )
    try:
        encoded = base64.b64encode(REMOTE_CHECK.encode()).decode()
        _, stdout, stderr = client.exec_command(
            f"printf %s {encoded} | base64 -d | bash", timeout=180
        )
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        print(output, end="")
        if error:
            print(error, end="")
        if code:
            raise RuntimeError(f"remote verification failed with exit code {code}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
