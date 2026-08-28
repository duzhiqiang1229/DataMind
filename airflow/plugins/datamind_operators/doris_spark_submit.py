"""Spark submit operator with DataMind/OpenLineage dataset metadata."""
import os
from urllib.parse import quote

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


OPENLINEAGE_LISTENER = "io.openlineage.spark.agent.OpenLineageSparkListener"
DEFAULT_OPENLINEAGE_JAR = "/opt/airflow/jars/openlineage-spark_2.13-1.52.0.jar"


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


class DorisSparkSubmitOperator(SparkSubmitOperator):
    """Submit a Doris PySpark job and expose its table lineage to OpenLineage.

    ``input_tables`` and ``output_tables`` should contain physical table names,
    preferably as ``database.table``. The Spark listener can add runtime
    datasets, while these explicit facets guarantee lineage for Doris
    connectors whose Spark logical plan does not expose the target relation.
    """

    template_fields = (
        *SparkSubmitOperator.template_fields,
        "input_tables",
        "output_tables",
        "datasource_name",
        "datasource_mapping",
        "default_database",
    )

    def __init__(
        self,
        *,
        input_tables: list[str] | tuple[str, ...] | None = None,
        output_tables: list[str] | tuple[str, ...] | None = None,
        datasource_name: str = "Doris 数仓",
        datasource_mapping: dict[str, str] | None = None,
        default_database: str | None = None,
        **kwargs,
    ) -> None:
        self.input_tables = list(input_tables or [])
        self.output_tables = list(output_tables or [])
        self.datasource_name = datasource_name
        self.datasource_mapping = {
            str(database).lower(): str(source_name)
            for database, source_name in (datasource_mapping or {}).items()
        }
        self.default_database = default_database

        lineage_jar = os.environ.get("SPARK_OPENLINEAGE_JAR", DEFAULT_OPENLINEAGE_JAR)
        configured_jars = str(kwargs.pop("jars", "") or "")
        jars = ",".join(item for item in (configured_jars, lineage_jar) if item)

        spark_conf = dict(kwargs.pop("conf", {}) or {})
        listeners = str(spark_conf.get("spark.extraListeners") or "")
        if OPENLINEAGE_LISTENER not in listeners.split(","):
            spark_conf["spark.extraListeners"] = ",".join(
                item for item in (listeners, OPENLINEAGE_LISTENER) if item
            )
        spark_conf.setdefault("spark.openlineage.namespace", "datamind-spark")
        kwargs.setdefault("openlineage_inject_parent_job_info", True)
        kwargs.setdefault("openlineage_inject_transport_info", True)
        super().__init__(jars=jars, conf=spark_conf, **kwargs)
        if not self.input_tables or not self.output_tables:
            self.log.warning(
                "DorisSparkSubmitOperator has incomplete explicit table lineage; "
                "relying on the Spark OpenLineage listener for runtime datasets."
            )

    def get_openlineage_facets_on_start(self):
        from airflow.providers.openlineage.extractors import OperatorLineage
        from openlineage.client.event_v2 import Dataset

        def dataset(value: str) -> Dataset | None:
            name = _table_name(value, self.default_database)
            if not name:
                return None
            source_name = _datasource_for_table(
                name, self.datasource_name, self.datasource_mapping
            )
            namespace = f"datamind://datasource/{quote(source_name, safe='')}"
            return Dataset(namespace=namespace, name=name)

        inputs = [item for value in self.input_tables if (item := dataset(value))]
        outputs = [item for value in self.output_tables if (item := dataset(value))]
        return OperatorLineage(inputs=inputs, outputs=outputs)
