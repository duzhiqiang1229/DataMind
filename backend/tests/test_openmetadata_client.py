"""OpenMetadata client contract tests for the 1.12 API."""

import httpx
import pytest

from app.integrations.openmetadata_client import OpenMetadataClient


@pytest.mark.asyncio
async def test_table_detail_uses_name_endpoint_and_jwt():
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json={"name": "orders", "columns": []})

    client = OpenMetadataClient({
        "base_url": "http://openmetadata-server:8585",
        "credentials": {"jwt_token": "test-bot-token"},
    })
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers=client._get_headers(),
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await client.get_table("service.db.public.orders")
    finally:
        await client.close()

    assert result["name"] == "orders"
    assert captured is not None
    assert captured.url.path == "/api/v1/tables/name/service.db.public.orders"
    assert captured.headers["Authorization"] == "Bearer test-bot-token"


@pytest.mark.asyncio
async def test_search_assets_normalizes_elasticsearch_hits():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["index"] == "dashboard_search_index"
        return httpx.Response(200, json={
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "hits": [{"_score": 1.2, "_source": {"name": "sales", "entityType": "dashboard"}}],
            }
        })

    client = OpenMetadataClient({"base_url": "http://openmetadata-server:8585"})
    client._client = httpx.AsyncClient(base_url=client.base_url, transport=httpx.MockTransport(handler))
    try:
        result = await client.search_assets("sales", "dashboard", limit=10)
    finally:
        await client.close()

    assert result["total"] == 1
    assert result["items"] == [{"name": "sales", "entityType": "dashboard", "_score": 1.2}]


@pytest.mark.asyncio
async def test_all_assets_uses_one_filtered_paginated_query():
    indexes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        index = request.url.params["index"]
        indexes.append(index)
        assert index == "all"
        assert request.url.params["from"] == "0"
        assert request.url.params["size"] == "20"
        assert "entityType:(table OR dashboard OR pipeline OR topic OR mlmodel OR container)" == request.url.params["q"]
        return httpx.Response(200, json={
            "hits": {
                "total": {"value": 6, "relation": "eq"},
                "hits": [{"_source": {"name": "orders", "entityType": "table", "updatedAt": 1}}],
            }
        })

    client = OpenMetadataClient({"base_url": "http://openmetadata-server:8585"})
    client._client = httpx.AsyncClient(base_url=client.base_url, transport=httpx.MockTransport(handler))
    try:
        result = await client.search_assets(entity_type="all", limit=20)
    finally:
        await client.close()

    assert result["total"] == 6
    assert indexes == ["all"]


def test_lineage_is_split_into_upstream_and_downstream_graphs():
    payload = {
        "entity": {"id": "center", "name": "orders", "fullyQualifiedName": "svc.db.orders"},
        "nodes": [
            {"id": "source", "name": "raw", "fullyQualifiedName": "svc.db.raw"},
            {"id": "target", "name": "report", "fullyQualifiedName": "svc.db.report"},
        ],
        "upstreamEdges": [{"fromEntity": "source", "toEntity": "center"}],
        "downstreamEdges": [{"fromEntity": "center", "toEntity": "target"}],
    }

    result = OpenMetadataClient._normalize_lineage(payload)

    assert [node["id"] for node in result["upstream"]["nodes"]] == ["source"]
    assert [node["id"] for node in result["downstream"]["nodes"]] == ["target"]
    assert result["upstream"]["edges"][0]["source"] == "svc.db.raw"
    assert result["downstream"]["edges"][0]["target"] == "svc.db.report"
