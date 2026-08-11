"""Async OpenMetadata REST client used by the data asset module."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any
from urllib.parse import quote

from app.integrations.base import ComponentAdapter


ASSET_INDEXES = {
    "all": "all",
    "table": "table_search_index",
    "dashboard": "dashboard_search_index",
    "pipeline": "pipeline_search_index",
    "topic": "topic_search_index",
    "mlmodel": "mlmodel_search_index",
    "container": "container_search_index",
}
ASSET_ENTITY_TYPES = tuple(key for key in ASSET_INDEXES if key != "all")


class OpenMetadataClient(ComponentAdapter):
    """Small, version-aware client for OpenMetadata 1.12.x APIs."""

    def __init__(self, config: dict):
        super().__init__("openmetadata", config)
        self._jwt_token: str = self._credentials.get("jwt_token", "")

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        return headers

    async def health_check(self) -> bool:
        try:
            # The server health endpoint lives on the non-public admin port.
            # The version endpoint is stable on the application port and still
            # verifies network reachability plus JWT authentication.
            response = await self._request("GET", "/api/v1/system/version")
            return response.status_code == 200 and bool(response.json().get("version"))
        except Exception:
            return False

    async def list_databases(self, limit: int = 100) -> list[dict]:
        response = await self._request("GET", "/api/v1/databases", params={"limit": limit})
        return response.json().get("data", [])

    async def list_tables(self, database_fqn: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {
            "limit": limit,
            "fields": "columns,owners,tags,domains,dataProducts,testSuite,usageSummary",
        }
        if database_fqn:
            params["database"] = database_fqn
        response = await self._request("GET", "/api/v1/tables", params=params)
        return response.json().get("data", [])

    async def get_table(self, table_fqn: str) -> dict:
        fields = (
            "columns,owners,tags,followers,domains,dataProducts,profile,testSuite,"
            "usageSummary,sampleData,tableConstraints,tablePartition,lifeCycle"
        )
        response = await self._request(
            "GET",
            f"/api/v1/tables/name/{quote(table_fqn, safe='')}",
            params={"fields": fields, "includeEmptyTestSuite": True},
        )
        return response.json()

    async def search_assets(
        self,
        query: str = "*",
        entity_type: str = "all",
        offset: int = 0,
        limit: int = 20,
        sort_field: str = "updatedAt",
        sort_order: str = "desc",
    ) -> dict:
        active_query = "deleted:false"
        if query and query != "*":
            active_query = f"({query}) AND {active_query}"

        if entity_type == "all":
            entity_filter = " OR ".join(ASSET_ENTITY_TYPES)
            scoped_query = f"{active_query} AND entityType:({entity_filter})"
            return await self._search_index(
                scoped_query, ASSET_INDEXES["all"], offset, limit, sort_field, sort_order,
            )
        index = ASSET_INDEXES.get(entity_type, ASSET_INDEXES["table"])
        return await self._search_index(
            active_query, index, offset, limit, sort_field, sort_order,
        )

    async def _search_index(
        self,
        query: str,
        index: str,
        offset: int,
        limit: int,
        sort_field: str,
        sort_order: str,
    ) -> dict:
        params: dict[str, Any] = {
            "q": query or "*",
            "index": index,
            "from": offset,
            "size": limit,
            "sortField": sort_field,
            "sortOrder": sort_order,
            "trackTotalHits": True,
        }
        response = await self._request(
            "GET",
            "/api/v1/search/query",
            params=params,
        )
        payload = response.json()
        hits = payload.get("hits", {})
        total = hits.get("total", 0)
        if isinstance(total, dict):
            total = total.get("value", 0)
        items = []
        for hit in hits.get("hits", []):
            item = hit.get("_source", {})
            item["_score"] = hit.get("_score")
            items.append(item)
        return {"items": items, "total": int(total or 0), "offset": offset, "limit": limit}

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        result = await self.search_assets(query=query, entity_type="table", limit=limit)
        return result["items"]

    async def get_lineage(
        self,
        entity_fqn: str,
        entity_type: str = "table",
        upstream_depth: int = 3,
        downstream_depth: int = 3,
    ) -> dict:
        response = await self._request(
            "GET",
            f"/api/v1/lineage/{quote(entity_type, safe='')}/name/{quote(entity_fqn, safe='')}",
            params={"upstreamDepth": upstream_depth, "downstreamDepth": downstream_depth},
        )
        return self._normalize_lineage(response.json())

    @staticmethod
    def _normalize_lineage(payload: dict) -> dict:
        center = payload.get("entity", {})
        nodes = [center, *payload.get("nodes", [])]
        by_id = {node.get("id"): node for node in nodes if node.get("id")}
        center_id = center.get("id")

        raw_edges = [*payload.get("upstreamEdges", []), *payload.get("downstreamEdges", [])]
        graph_edges = []
        outgoing: dict[str, list[str]] = {}
        incoming: dict[str, list[str]] = {}
        for edge in raw_edges:
            source_id, target_id = edge.get("fromEntity"), edge.get("toEntity")
            if not source_id or not target_id:
                continue
            outgoing.setdefault(source_id, []).append(target_id)
            incoming.setdefault(target_id, []).append(source_id)
            source = by_id.get(source_id, {})
            target = by_id.get(target_id, {})
            graph_edges.append({
                "source": source.get("fullyQualifiedName") or source_id,
                "target": target.get("fullyQualifiedName") or target_id,
                "lineageDetails": edge.get("lineageDetails"),
            })

        def reachable(adjacency: dict[str, list[str]]) -> set[str]:
            seen: set[str] = set()
            queue = deque([center_id] if center_id else [])
            while queue:
                current = queue.popleft()
                for neighbor in adjacency.get(current, []):
                    if neighbor not in seen and neighbor != center_id:
                        seen.add(neighbor)
                        queue.append(neighbor)
            return seen

        upstream_ids = reachable(incoming)
        downstream_ids = reachable(outgoing)

        def section(ids: set[str]) -> dict:
            section_nodes = [by_id[node_id] for node_id in ids if node_id in by_id]
            fqns = {node.get("fullyQualifiedName") or node.get("id") for node in section_nodes}
            center_fqn = center.get("fullyQualifiedName") or center_id
            edges = [
                edge for edge in graph_edges
                if (edge["source"] in fqns or edge["source"] == center_fqn)
                and (edge["target"] in fqns or edge["target"] == center_fqn)
            ]
            return {"nodes": section_nodes, "edges": edges}

        return {
            "entity": center,
            "upstream": section(upstream_ids),
            "downstream": section(downstream_ids),
        }

    async def list_test_cases(self, table_fqn: str | None = None, limit: int = 100) -> dict:
        params: dict[str, Any] = {
            "limit": limit,
            "fields": "owners,testSuite,testDefinition,testCaseResult",
            "orderByLastExecutionDate": True,
            "includeAllTests": True,
        }
        if table_fqn:
            params["entityLink"] = f"<#E::table::{table_fqn}>"
        response = await self._request("GET", "/api/v1/dataQuality/testCases", params=params)
        payload = response.json()
        return {"items": payload.get("data", []), "total": payload.get("paging", {}).get("total", 0)}

    async def governance(self, limit: int = 100) -> dict:
        async def listing(path: str, fields: str | None = None) -> list[dict]:
            params: dict[str, Any] = {"limit": limit}
            if fields:
                params["fields"] = fields
            response = await self._request("GET", path, params=params)
            return response.json().get("data", [])

        domains, products, glossaries, terms, classifications = await asyncio.gather(
            listing("/api/v1/domains"),
            listing("/api/v1/dataProducts"),
            listing("/api/v1/glossaries"),
            listing("/api/v1/glossaryTerms", "owners,tags,domains,relatedTerms,reviewers,children"),
            listing("/api/v1/classifications"),
        )
        return {
            "domains": domains,
            "dataProducts": products,
            "glossaries": glossaries,
            "glossaryTerms": terms,
            "classifications": classifications,
        }

    async def summary(self) -> dict:
        entity_types = [key for key in ASSET_INDEXES if key != "all"]
        searches = await asyncio.gather(*[
            self.search_assets(entity_type=entity_type, limit=1)
            for entity_type in entity_types
        ])
        counts = {entity_type: result["total"] for entity_type, result in zip(entity_types, searches)}
        table_total = counts.get("table", 0)
        sample_size = min(table_total, 1000)
        tables = (
            (await self.search_assets(entity_type="table", limit=sample_size))["items"]
            if sample_size else []
        )

        def covered(field: str) -> int:
            return sum(1 for table in tables if table.get(field))

        denominator = len(tables) or 1
        quality = await self.list_test_cases(limit=1000)
        statuses: dict[str, int] = {"Success": 0, "Failed": 0, "Aborted": 0}
        for case in quality["items"]:
            status = (case.get("testCaseResult") or {}).get("testCaseStatus")
            if status:
                statuses[status] = statuses.get(status, 0) + 1
        return {
            "totalAssets": sum(counts.values()),
            "counts": counts,
            "coverage": {
                "description": round(covered("description") * 100 / denominator),
                "owners": round(covered("owners") * 100 / denominator),
                "tags": round(covered("tags") * 100 / denominator),
                "domains": round(covered("domains") * 100 / denominator),
            },
            "quality": {"total": quality["total"], "statuses": statuses},
            "sampledTables": len(tables),
        }

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
