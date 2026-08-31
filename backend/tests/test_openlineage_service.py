import unittest
from datetime import datetime, timezone

from app.services.openlineage_service import (
    extract_airflow_identity,
    extract_datasets,
    extract_parent_run_id,
)


class OpenLineageEventTests(unittest.TestCase):
    def test_extracts_airflow_task_identity(self):
        event = {
            "run": {
                "runId": "11111111-1111-1111-1111-111111111111",
                "facets": {
                    "airflow": {
                        "dag": {"dag_id": "dwd_daily"},
                        "dagRun": {
                            "dag_id": "dwd_daily",
                            "run_id": "scheduled__2026-08-26T00:00:00+00:00",
                            "run_type": "scheduled",
                            "start_date": "2026-08-26T00:00:00+00:00",
                        },
                        "task": {"task_id": "load_fees", "operator_class": "DorisSparkSubmitOperator"},
                        "taskInstance": {
                            "try_number": 2,
                            "start_date": "2026-08-26T00:05:00+00:00",
                        },
                    }
                },
            },
            "job": {"namespace": "datamind-airflow", "name": "dwd_daily.load_fees"},
        }

        identity = extract_airflow_identity(event)

        self.assertIsNotNone(identity)
        self.assertEqual(identity["dag_id"], "dwd_daily")
        self.assertEqual(identity["task_id"], "load_fees")
        self.assertEqual(identity["try_number"], 2)
        self.assertEqual(
            identity["start_date"],
            datetime(2026, 8, 26, 0, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(identity["openlineage_run_id"], "11111111-1111-1111-1111-111111111111")

    def test_does_not_use_dag_start_as_task_start(self):
        event = {
            "run": {
                "facets": {
                    "airflow": {
                        "dagRun": {
                            "dag_id": "dwd_daily",
                            "run_id": "manual__2026-08-26T00:00:00+00:00",
                            "start_date": "2026-08-26T00:00:00+00:00",
                        },
                        "task": {"task_id": "load_fees"},
                        "taskInstance": {"try_number": 1},
                    }
                }
            }
        }

        identity = extract_airflow_identity(event)

        self.assertIsNotNone(identity)
        self.assertIsNone(identity["start_date"])

    def test_extracts_spark_parent_and_deduplicates_datasets(self):
        event = {
            "run": {
                "facets": {
                    "parent": {"run": {"runId": "airflow-parent-run"}},
                }
            },
            "inputs": [
                {"namespace": "jdbc:mysql://doris:9030", "name": "dwd.fees"},
                {"namespace": "jdbc:mysql://doris:9030", "name": "dwd.fees"},
            ],
        }

        self.assertEqual(extract_parent_run_id(event), "airflow-parent-run")
        self.assertEqual(
            extract_datasets(event, "inputs"),
            [{"namespace": "jdbc:mysql://doris:9030", "name": "dwd.fees"}],
        )


if __name__ == "__main__":
    unittest.main()
