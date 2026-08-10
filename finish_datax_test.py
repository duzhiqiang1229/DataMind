# -*- coding: utf-8 -*-
"""Update datax_home to /home/datax, redeploy DAG, rebuild task and trigger."""
import json
import urllib.request


def call(method, path, payload=None, token=None):
    req = urllib.request.Request(
        f"http://localhost:8000{path}",
        method=method,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


login = call("POST", "/api/v1/auth/login", {"username": "admin", "password": "admin123"})
token = login["data"]["access_token"]

# 1. Update DataX component config
existing = call("GET", "/api/v1/components/by-code/datax", token=token)["data"]
config = existing.get("config_json") or {}
config["datax_home"] = "/home/datax"
call("PUT", "/api/v1/components/by-code/datax", {
    "component_name": "DataX 数据同步",
    "config_json": config,
    "status": "active",
}, token)
print("datax_home updated to /home/datax")

# 2. Redeploy DAGs to Airflow
r = call("POST", "/api/v1/airflow/deploy-dags", token=token)
print("deploy:", r["code"], r.get("data", {}).get("uploaded"))

# 3. Delete old test task and rebuild (regenerate job JSON with selectedDatabase)
items = call("GET", "/api/v1/datax-tasks?page=1&page_size=100", token=token)["data"]["items"]
for t in items:
    if t.get("task_code") == "test_sync_user_login":
        call("DELETE", f"/api/v1/datax-tasks/{t['id']}", token=token)
        print("old task deleted")

payload = {
    "task_name": "测试同步-user_login_log",
    "task_code": "test_sync_user_login",
    "source_datasource_id": "0f66e454-dcf3-48a0-9531-18da986176e1",
    "source_table": "user_login_log",
    "target_database": "test",
    "target_table": "user_login_log_sync",
    "sync_mode": "full",
    "channel": 3,
    "field_mappings": [
        {"source_column": "id", "target_column": "id", "source_type": "INT", "target_type": "INT", "is_primary_key": True, "sort_order": 0},
        {"source_column": "user_id", "target_column": "user_id", "source_type": "INT", "target_type": "INT", "is_primary_key": False, "sort_order": 1},
        {"source_column": "login_time", "target_column": "login_time", "source_type": "DATETIME", "target_type": "DATETIME", "is_primary_key": False, "sort_order": 2},
    ],
}
r = call("POST", "/api/v1/datax-tasks", payload, token)
print("task rebuilt:", r["code"], r.get("data", {}).get("task_code"))
job = json.dumps(r.get("data", {}).get("job_config", {}))
print("has selectedDatabase:", "selectedDatabase" in job)

# 4. Trigger
task_id = r["data"]["id"]
r = call("POST", f"/api/v1/datax-tasks/{task_id}/trigger", {"run_immediately": True}, token)
print("trigger:", r["code"], r.get("data", {}).get("status"), r.get("data", {}).get("dag_run_id"))
