from unittest.mock import AsyncMock

import pytest

from app.services import airflow_service


@pytest.mark.asyncio
async def test_retry_dag_run_uses_clear_endpoint(monkeypatch):
    response = type(
        "Response",
        (),
        {"content": b"{}", "json": lambda self: {}},
    )()
    client = type("Client", (), {"_request": AsyncMock(return_value=response)})()
    monkeypatch.setattr(
        airflow_service,
        "get_airflow_client",
        AsyncMock(return_value=client),
    )

    result = await airflow_service.retry_dag_run(
        object(), "etl_dim_to_ads", "manual__validation", "load_dwd"
    )

    assert result["success"] is True
    client._request.assert_awaited_once_with(
        "POST",
        "/api/v1/dags/etl_dim_to_ads/clearTaskInstances",
        json={
            "dag_run_id": "manual__validation",
            "task_ids": ["load_dwd"],
            "only_failed": True,
            "include_downstream": True,
            "reset_dag_runs": True,
            "dry_run": False,
        },
    )
