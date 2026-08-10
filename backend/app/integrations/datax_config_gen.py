"""
DataX job JSON generator.
Generates DataX job configuration from user-friendly task config stored in PostgreSQL.
Does NOT execute DataX — execution is delegated to Airflow DAG.

The generated JSON is stored in the database and passed to Airflow DAG at trigger time.
"""
from typing import Any
from loguru import logger


class DataXConfigGenerator:
    """
    Generates DataX job JSON from DataMind task configuration.

    DataX job structure (simplified):
    {
        "job": {
            "content": [{
                "reader": {
                    "name": "mysqlreader" | "oraclereader" | ...,
                    "parameter": {
                        "username", "password", "connection": [{
                            "jdbcUrl": [...], "table": [...], "column": [...]
                        }],
                        "where": "...",
                        "splitPk": "id"
                    }
                },
                "writer": {
                    "name": "doriswriter" | "mysqlwriter" | ...,
                    "parameter": {
                        "username", "password", "connection": {
                            "jdbcUrl", "database", "table", "column": [...]
                        },
                        "loadProps": {"format": "json", "strip_external": "true"}
                    }
                }
            }],
            "setting": {
                "speed": { "channel": 3 },
                "errorLimit": { "record": 0, "percentage": 0.02 }
            }
        }
    }
    """

    # Map DataMind source type to DataX reader plugin name
    READER_MAP = {
        "mysql": "mysqlreader",
        "oracle": "oraclereader",
        "postgresql": "postgresqlreader",
        "sqlserver": "sqlserverreader",
    }

    # Map target type to DataX writer plugin name
    WRITER_MAP = {
        "doris": "doriswriter",
        "mysql": "mysqlwriter",
        "postgresql": "postgresqlwriter",
    }

    def generate_job_json(
        self,
        source_config: dict,
        target_config: dict,
        column_mapping: list[dict],
        options: dict,
    ) -> dict:
        """
        Generate a complete DataX job JSON.

        Args:
            source_config: {
                "type": "mysql", "host": "...", "port": 3306,
                "username": "...", "password": "...", "database": "...",
                "table": "...", "where": "1=1", "split_pk": "id"
            }
            target_config: {
                "type": "doris", "host": "...", "port": 9030,
                "username": "...", "password": "...", "database": "...",
                "table": "..."
            }
            column_mapping: [
                {"source_column": "user_id", "target_column": "user_id", "source_type": "BIGINT"},
                ...
            ]
            options: {
                "channel": 3, "error_limit_record": 0, "error_limit_percentage": 0.02
            }

        Returns:
            DataX job JSON dict (stored in database, passed to Airflow at trigger)
        """
        source_type = source_config.get("type", "mysql")
        target_type = target_config.get("type", "doris")

        reader_name = self.READER_MAP.get(source_type)
        writer_name = self.WRITER_MAP.get(target_type)

        if not reader_name:
            raise ValueError(f"Unsupported source type: {source_type}")
        if not writer_name:
            raise ValueError(f"Unsupported target type: {target_type}")

        # Extract column lists
        source_columns = [m["source_column"] for m in column_mapping]
        target_columns = [m["target_column"] for m in column_mapping]

        # Build reader
        reader = {
            "name": reader_name,
            "parameter": {
                "username": source_config["username"],
                "password": source_config["password"],
                "connection": [{
                    "jdbcUrl": [
                        self._build_jdbc_url(source_type, source_config)
                    ],
                    "table": [source_config["table"]],
                    "selectedDatabase": source_config.get("database", ""),
                }],
                "column": source_columns,
            },
        }

        # Optional where clause and split key
        if source_config.get("where"):
            reader["parameter"]["where"] = source_config["where"]
        if source_config.get("split_pk"):
            reader["parameter"]["splitPk"] = source_config["split_pk"]

        # Build writer
        writer = {
            "name": writer_name,
            "parameter": {
                "username": target_config["username"],
                "password": target_config["password"],
                "column": target_columns,
                "connection": [{
                    "jdbcUrl": self._build_jdbc_url(target_type, target_config),
                    "selectedDatabase": target_config["database"],
                    "table": [target_config["table"]],
                }],
                "loadUrl": [
                    f"{target_config['host']}:{target_config.get('http_port', 8030)}"
                ],
                "loadProps": options.get("load_props", {
                    "format": "json",
                    "strip_outer_array": "true",
                }),
            },
        }

        # Build job
        job = {
            "job": {
                "content": [{
                    "reader": reader,
                    "writer": writer,
                }],
                "setting": {
                    "speed": {
                        "channel": options.get("channel", 3),
                    },
                    "errorLimit": {
                        "record": options.get("error_limit_record", 0),
                        "percentage": options.get("error_limit_percentage", 0.02),
                    },
                },
            }
        }

        logger.info(f"DataX job JSON generated: {source_config['table']} -> {target_config['table']}")
        return job

    def _build_jdbc_url(self, db_type: str, config: dict) -> str:
        """Build JDBC URL based on database type."""
        host = config["host"]
        port = config["port"]
        database = config["database"]

        if db_type == "mysql":
            return f"jdbc:mysql://{host}:{port}/{database}?useUnicode=true&characterEncoding=utf-8"
        elif db_type == "oracle":
            return f"jdbc:oracle:thin:@{host}:{port}:{database}"
        elif db_type == "postgresql":
            return f"jdbc:postgresql://{host}:{port}/{database}"
        elif db_type == "doris":
            return f"jdbc:mysql://{host}:{port}/{database}"
        else:
            return f"jdbc:{db_type}://{host}:{port}/{database}"


# Singleton
datax_config_gen = DataXConfigGenerator()
