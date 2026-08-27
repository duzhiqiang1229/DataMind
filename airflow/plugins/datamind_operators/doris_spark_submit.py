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
        "default_database",
    )

    def __init__(
        self,
        *,
        input_tables: list[str] | tuple[str, ...] | None = None,
        output_tables: list[str] | tuple[str, ...] | None = None,
        datasource_name: str = "Doris 数仓",
        default_database: str | None = None,
        **kwargs,
    ) -> None:
        self.input_tables = list(input_tables or [])
        self.output_tables = list(output_tables or [])
        self.datasource_name = datasource_name
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

        namespace = f"datamind://datasource/{quote(self.datasource_name, safe='')}"
        inputs = [
            Dataset(namespace=namespace, name=name)
            for name in (_table_name(item, self.default_database) for item in self.input_tables)
            if name
        ]
        outputs = [
            Dataset(namespace=namespace, name=name)
            for name in (_table_name(item, self.default_database) for item in self.output_tables)
            if name
        ]
        return OperatorLineage(inputs=inputs, outputs=outputs)
