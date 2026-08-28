"""Doris SQL operator with reliable OpenLineage table facets."""
from urllib.parse import quote

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


def _table_name(value: str, default_database: str | None) -> str:
    parts = [part.strip("`\" ") for part in str(value).split(".") if part.strip("`\" ")]
    if len(parts) == 1 and default_database:
        parts.insert(0, default_database)
    return ".".join(parts)


def _datasource_for_table(
    table_name: str,
    datasource_name: str,
    datasource_mapping: dict[str, str],
) -> str:
    parts = [part.strip("`\" ") for part in table_name.split(".") if part.strip("`\" ")]
    database = parts[-2].lower() if len(parts) >= 2 else ""
    return datasource_mapping.get(database, datasource_name)


class DorisSQLOperator(SQLExecuteQueryOperator):
    """Execute Doris SQL and emit explicit or SQL-parser-derived lineage."""

    template_fields = (
        *SQLExecuteQueryOperator.template_fields,
        "input_tables",
        "output_tables",
        "datasource_name",
        "datasource_mapping",
    )

    def __init__(
        self,
        *,
        datasource_name: str = "Doris 数仓",
        datasource_mapping: dict[str, str] | None = None,
        input_tables: list[str] | tuple[str, ...] | None = None,
        output_tables: list[str] | tuple[str, ...] | None = None,
        **kwargs,
    ) -> None:
        self.datasource_name = datasource_name
        self.datasource_mapping = {
            str(database).lower(): str(source_name)
            for database, source_name in (datasource_mapping or {}).items()
        }
        self.input_tables = list(input_tables or [])
        self.output_tables = list(output_tables or [])
        super().__init__(**kwargs)

    def get_openlineage_facets_on_start(self):
        if not self.input_tables and not self.output_tables:
            return super().get_openlineage_facets_on_start()

        from airflow.providers.openlineage.extractors import OperatorLineage
        from openlineage.client.event_v2 import Dataset

        def dataset(value: str) -> Dataset | None:
            name = _table_name(value, self.database)
            if not name:
                return None
            source_name = _datasource_for_table(
                name, self.datasource_name, self.datasource_mapping
            )
            namespace = f"datamind://datasource/{quote(source_name, safe='')}"
            return Dataset(namespace=namespace, name=name)

        inputs = [item for value in self.input_tables if (item := dataset(value))]
        outputs = [item for value in self.output_tables if (item := dataset(value))]
        explicit = OperatorLineage(inputs=inputs, outputs=outputs)
        if inputs and outputs:
            return explicit
        try:
            parsed = super().get_openlineage_facets_on_start()
        except Exception as exc:
            self.log.warning("SQL parser lineage unavailable; using explicit Doris datasets: %s", exc)
            parsed = None
        return explicit.merge(parsed) if parsed else explicit
