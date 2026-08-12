"""Reproducible structural analysis of the OpenMetadata warehouse snapshot."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
snapshot = json.loads((ROOT / "source_snapshot.json").read_text(encoding="utf-8"))
tables = snapshot["warehouseTables"]
pipeline = snapshot["pipeline"]
lineage = snapshot["pipelineLineage"]


def layer_of(fqn: str) -> str:
    parts = fqn.split(".")
    return parts[-2] if len(parts) >= 2 and parts[-2] in {"ods", "dim", "dwd", "dws", "ads"} else "other"


layers: dict[str, list[dict]] = defaultdict(list)
for table in tables:
    layers[layer_of(table.get("fullyQualifiedName", ""))].append(table)

layer_rows = []
for layer in ("ods", "dim", "dwd", "dws", "ads"):
    items = layers[layer]
    column_count = sum(len(item.get("columns") or []) for item in items)
    layer_rows.append({
        "layer": layer.upper(),
        "tables": len(items),
        "columns": column_count,
        "avg_columns": round(column_count / len(items), 1) if items else 0,
        "with_owner": sum(bool(item.get("owners")) for item in items),
        "with_tags": sum(bool(item.get("tags")) for item in items),
        "with_tests": sum(bool(item.get("testSuite")) for item in items),
        "with_profile": sum(bool(item.get("profile")) for item in items),
    })

operator_counts = Counter(task.get("taskType") or "Unknown" for task in pipeline.get("tasks") or [])
task_dependency_edges = sum(len(task.get("downstreamTasks") or []) for task in pipeline.get("tasks") or [])
task_names = {task.get("name") for task in pipeline.get("tasks") or []}
task_adjacency = {
    task.get("name"): list(task.get("downstreamTasks") or [])
    for task in pipeline.get("tasks") or []
}


def longest_task_path() -> list[str]:
    """Return the longest acyclic path in the Airflow task graph."""
    cache: dict[str, list[str]] = {}

    def visit(task_name: str, active: set[str]) -> list[str]:
        if task_name in cache:
            return cache[task_name]
        if task_name in active:
            return [task_name]
        candidates = [
            visit(child, active | {task_name})
            for child in task_adjacency.get(task_name, [])
        ]
        tail = max(candidates, key=len) if candidates else []
        cache[task_name] = [task_name, *tail]
        return cache[task_name]

    return max((visit(name, set()) for name in task_adjacency), key=len, default=[])

all_graph_edges = [*lineage["upstream"]["edges"], *lineage["downstream"]["edges"]]
unique_pairs = {(edge["source"], edge["target"]) for edge in all_graph_edges}
column_lineage_pairs = sum(
    len((edge.get("lineageDetails") or {}).get("columnsLineage") or [])
    for edge in all_graph_edges
)
unique_column_pairs = set()
edges_with_column_lineage = 0
for edge in all_graph_edges:
    mappings = (edge.get("lineageDetails") or {}).get("columnsLineage") or []
    if mappings:
        edges_with_column_lineage += 1
    for mapping in mappings:
        from_columns = tuple(sorted(mapping.get("fromColumns") or []))
        to_column = mapping.get("toColumn")
        if from_columns or to_column:
            unique_column_pairs.add((from_columns, to_column))

job_pattern = re.compile(r"job:\s+datamind_airflow/etl_dim_to_ads\.([^\s(]+)")
job_io: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"inputs": set(), "outputs": set()})
for edge in all_graph_edges:
    details = edge.get("lineageDetails") or {}
    match = job_pattern.search(details.get("description") or "")
    if not match:
        continue
    job = match.group(1)
    source, target = edge["source"], edge["target"]
    if target == pipeline["fullyQualifiedName"]:
        job_io[job]["inputs"].add(source)
    elif source == pipeline["fullyQualifiedName"]:
        job_io[job]["outputs"].add(target)
    else:
        # Some OpenLineage events are materialized directly as table-to-table
        # edges instead of being routed through the pipeline entity.
        job_io[job]["inputs"].add(source)
        job_io[job]["outputs"].add(target)

job_rows = []
for job, io in sorted(job_io.items()):
    input_layers = sorted({layer_of(value).upper() for value in io["inputs"]})
    output_layers = sorted({layer_of(value).upper() for value in io["outputs"]})
    job_rows.append({
        "task": job,
        "inputs": len(io["inputs"]),
        "outputs": len(io["outputs"]),
        "input_layers": ", ".join(input_layers),
        "output_layers": ", ".join(output_layers),
        "input_tables": sorted(value.split(".")[-1] for value in io["inputs"]),
        "output_tables": sorted(value.split(".")[-1] for value in io["outputs"]),
    })

observed_job_names = set(job_io)
missing_jobs = sorted(task_names - observed_job_names)
used_ods_tables = sorted({
    value.split(".")[-1]
    for io in job_io.values()
    for value in io["inputs"]
    if layer_of(value) == "ods"
})
all_ods_tables = sorted(table["name"] for table in layers["ods"])
unused_ods_tables = sorted(set(all_ods_tables) - set(used_ods_tables))
served_dws_tables = sorted({
    value.split(".")[-1]
    for io in job_io.values()
    for value in io["inputs"]
    if layer_of(value) == "dws"
    for output in io["outputs"]
    if layer_of(output) == "ads"
})

domains = snapshot["governance"]["domains"]
classifications = snapshot["governance"]["classifications"]
owners = []
for table in tables:
    if table.get("owners"):
        owners.append({
            "table": table["fullyQualifiedName"],
            "owners": [owner.get("displayName") or owner.get("name") for owner in table["owners"]],
        })

analysis = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "sourceGeneratedAt": snapshot["generatedAt"],
    "assetSummary": snapshot["summary"],
    "layerRows": layer_rows,
    "layerTables": {
        layer.upper(): sorted(table["name"] for table in items)
        for layer, items in layers.items()
    },
    "pipeline": {
        "name": pipeline["fullyQualifiedName"],
        "description": pipeline.get("description"),
        "scheduleInterval": pipeline.get("scheduleInterval"),
        "tasks": len(pipeline.get("tasks") or []),
        "operatorCounts": dict(operator_counts),
        "taskDependencyEdges": task_dependency_edges,
        "upstreamNodes": len({node.get("fullyQualifiedName") for node in lineage["upstream"]["nodes"]}),
        "downstreamNodes": len({node.get("fullyQualifiedName") for node in lineage["downstream"]["nodes"]}),
        "uniqueLineagePairs": len(unique_pairs),
        "rawLineageRecords": len(all_graph_edges),
        "columnLineageMappings": column_lineage_pairs,
        "uniqueColumnLineageMappings": len(unique_column_pairs),
        "edgesWithColumnLineage": edges_with_column_lineage,
        "openLineageTasksObserved": len(job_rows),
        "missingOpenLineageTasks": missing_jobs,
        "longestTaskPathLength": len(longest_task_path()),
        "longestTaskPath": longest_task_path(),
        "maxTaskFanOut": max((len(children) for children in task_adjacency.values()), default=0),
        "tasksWithFanOut": sum(len(children) > 1 for children in task_adjacency.values()),
        "usedOdsTables": len(used_ods_tables),
        "unusedOdsTables": unused_ods_tables,
        "servedDwsTables": served_dws_tables,
    },
    "jobLineage": job_rows,
    "governance": {
        "domains": [{"name": item.get("name"), "displayName": item.get("displayName")} for item in domains],
        "dataProducts": len(snapshot["governance"]["dataProducts"]),
        "glossaries": len(snapshot["governance"]["glossaries"]),
        "glossaryTerms": len(snapshot["governance"]["glossaryTerms"]),
        "classifications": [item.get("name") for item in classifications],
        "ownedTables": owners,
    },
    "metadataHealth": {
        "describedTables": sum(bool(table.get("description")) for table in tables),
        "ownedTables": len(owners),
        "taggedTables": sum(bool(table.get("tags")) for table in tables),
        "domainAssignedTables": sum(bool(table.get("domains")) for table in tables),
        "profiledTables": sum(bool(table.get("profile")) for table in tables),
        "testedTables": sum(bool(table.get("testSuite")) for table in tables),
        "partitionedTables": sum(bool(table.get("tablePartition")) for table in tables),
        "constrainedTables": sum(bool(table.get("tableConstraints")) for table in tables),
        "totalColumns": sum(len(table.get("columns") or []) for table in tables),
    },
}

(ROOT / "analysis_summary.json").write_text(
    json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(analysis, ensure_ascii=False, indent=2))
