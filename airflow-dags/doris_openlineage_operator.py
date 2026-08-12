"""SparkSubmitOperator with automatic Doris table lineage extraction.

The OpenLineage Spark agent cannot currently extract datasets from the Doris
Spark Connector's DataSource V2 relations.  DataMind jobs consistently read
through ``read_doris("schema.table", ...)`` and write with
``.option("doris.table.identifier", "schema.table")``.  This operator parses
those declarations and reports them as OpenLineage datasets automatically.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.common.compat.openlineage.facet import Dataset
from airflow.providers.openlineage.extractors import OperatorLineage


DORIS_SERVICE = "数据仓库"
DORIS_DATABASE = "数据仓库"
DORIS_IDENTIFIER_OPTION = "doris.table.identifier"


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _valid_identifier(value: str | None) -> bool:
    if not value or value.count(".") != 1:
        return False
    schema, table = value.split(".", 1)
    return bool(schema and table) and schema in {"ods", "dim", "dwd", "dws", "ads"}


def extract_doris_identifiers(source: str) -> tuple[set[str], set[str]]:
    """Return the input and output ``schema.table`` identifiers in a job."""
    tree = ast.parse(source)
    inputs: set[str] = set()
    outputs: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if _call_name(node) == "read_doris" and node.args:
            identifier = _literal_string(node.args[0])
            if _valid_identifier(identifier):
                inputs.add(identifier)

        if _call_name(node) == "option" and len(node.args) >= 2:
            option = _literal_string(node.args[0])
            identifier = _literal_string(node.args[1])
            if option == DORIS_IDENTIFIER_OPTION and _valid_identifier(identifier):
                outputs.add(identifier)

    # A literal table used by both patterns is a source, not an output. This
    # protects jobs that use a direct literal option while reading.
    outputs.difference_update(inputs)
    return inputs, outputs


def _datasets(identifiers: Iterable[str]) -> list[Dataset]:
    return [
        Dataset(namespace=DORIS_SERVICE, name=f"{DORIS_DATABASE}.{identifier}")
        for identifier in sorted(set(identifiers))
    ]


class DorisSparkSubmitOperator(SparkSubmitOperator):
    """Spark submit operator that emits Doris lineage on task completion."""

    def _doris_lineage(self) -> OperatorLineage:
        application = self.application
        if not isinstance(application, str):
            return OperatorLineage()
        try:
            source = Path(application).read_text(encoding="utf-8")
            inputs, outputs = extract_doris_identifiers(source)
        except (OSError, SyntaxError, UnicodeError):
            self.log.exception("Unable to extract Doris lineage from %s", application)
            return OperatorLineage()
        return OperatorLineage(inputs=_datasets(inputs), outputs=_datasets(outputs))

    def get_openlineage_facets_on_complete(self, task_instance) -> OperatorLineage:
        return self._doris_lineage()
