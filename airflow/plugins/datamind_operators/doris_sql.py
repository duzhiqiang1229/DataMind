"""Doris SQL operator with reliable OpenLineage table facets."""
from urllib.parse import quote

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


def _table_name(value: str, default_database: str | None) -> str:
    parts = [part.strip("`\" ") for part in str(value).split(".") if part.strip("`\" ")]
    if len(parts) == 1 and default_database:
        parts.insert(0, default_database)
    return ".".join(parts)


class DorisSQLOperator(SQLExecuteQueryOperator):
    """Execute Doris SQL and emit explicit or SQL-parser-derived lineage."""

    template_fields = (
        *SQLExecuteQueryOperator.template_fields,
        "input_tables",
        "output_tables",
        "datasource_name",
    )

    def __init__(
        self,
        *,
        datasource_name: str = "Doris 数仓",
        input_tables: list[str] | tuple[str, ...] | None = None,
        output_tables: list[str] | tuple[str, ...] | None = None,
        **kwargs,
    ) -> None:
        self.datasource_name = datasource_name
        self.input_tables = list(input_tables or [])
        self.output_tables = list(output_tables or [])
        super().__init__(**kwargs)

    def get_openlineage_facets_on_start(self):
        if not self.input_tables and not self.output_tables:
            return super().get_openlineage_facets_on_start()

        from airflow.providers.openlineage.extractors import OperatorLineage
        from openlineage.client.event_v2 import Dataset

        namespace = f"datamind://datasource/{quote(self.datasource_name, safe='')}"
        inputs = [
            Dataset(namespace=namespace, name=name)
            for name in (_table_name(item, self.database) for item in self.input_tables)
            if name
        ]
        outputs = [
            Dataset(namespace=namespace, name=name)
            for name in (_table_name(item, self.database) for item in self.output_tables)
            if name
        ]
        explicit = OperatorLineage(inputs=inputs, outputs=outputs)
        if inputs and outputs:
            return explicit
        try:
            parsed = super().get_openlineage_facets_on_start()
        except Exception as exc:
            self.log.warning("SQL parser lineage unavailable; using explicit Doris datasets: %s", exc)
            parsed = None
        return explicit.merge(parsed) if parsed else explicit
