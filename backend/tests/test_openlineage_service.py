import unittest

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
                        },
                        "task": {"task_id": "load_fees", "operator_class": "DorisSparkSubmitOperator"},
                        "taskInstance": {"try_number": 2},
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
        self.assertEqual(identity["openlineage_run_id"], "11111111-1111-1111-1111-111111111111")

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
