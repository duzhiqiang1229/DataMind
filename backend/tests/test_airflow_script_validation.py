import unittest

from app.services.airflow_service import inspect_dag_python


class AirflowScriptValidationTests(unittest.TestCase):
    def test_detects_pyspark_import_inside_task_callable(self):
        result = inspect_dag_python(
            "def run():\n"
            "    from pyspark.sql import SparkSession\n"
            "    return SparkSession\n"
        )

        self.assertTrue(result["uses_pyspark"])
        self.assertEqual(result["runtime"], "pyspark")
        self.assertIn("pyspark.sql", result["imports"])

    def test_accepts_regular_python(self):
        result = inspect_dag_python("from airflow.sdk import DAG\n")

        self.assertFalse(result["uses_pyspark"])
        self.assertEqual(result["runtime"], "python")

    def test_rejects_invalid_python_before_writing_dag(self):
        with self.assertRaisesRegex(ValueError, "Python语法错误"):
            inspect_dag_python("def broken(:\n    pass\n")


if __name__ == "__main__":
    unittest.main()
