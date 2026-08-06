"""
Doris client: MySQL protocol query + HTTP admin API.
Uses pymysql for SQL execution (port 9030), HTTP for admin (port 8030).
"""
from typing import Any, Optional

import pymysql
from loguru import logger

from app.integrations.base import ComponentAdapter


class DorisClient(ComponentAdapter):
    """Doris OLAP query client via MySQL wire protocol."""

    def __init__(self, config: dict):
        super().__init__("doris", config)
        # MySQL protocol host/port (usually 9030)
        self.mysql_host: str = config.get("mysql_host", config.get("host", ""))
        self.mysql_port: int = config.get("mysql_port", 9030)
        # HTTP API host/port (usually 8030)
        self.http_port: int = config.get("http_port", 8030)
        self.username: str = self._credentials.get("username", "root")
        self.password: str = self._credentials.get("password", "")
        self.database: str = config.get("default_database", "")

    async def health_check(self) -> bool:
        """Test MySQL protocol connectivity."""
        try:
            conn = self._get_mysql_conn()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[Doris] Health check failed: {e}")
            return False

    def _get_mysql_conn(self, database: Optional[str] = None) -> pymysql.Connection:
        """Create a synchronous MySQL connection to Doris."""
        db = database or self.database
        return pymysql.connect(
            host=self.mysql_host,
            port=self.mysql_port,
            user=self.username,
            password=self.password,
            database=db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=300,
        )

    async def execute_query(
        self,
        sql: str,
        database: Optional[str] = None,
        limit: int = 10000,
    ) -> dict:
        """
        Execute a SELECT query on Doris and return results.

        Returns:
            {
                "columns": ["col1", "col2"],
                "rows": [{"col1": val, "col2": val}],
                "row_count": 100,
                "elapsed_ms": 15
            }
        """
        import time
        start = time.time()

        conn = self._get_mysql_conn(database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchmany(limit + 1)  # fetch one extra to detect truncation

            truncated = len(rows) > limit
            if truncated:
                rows = rows[:limit]

            elapsed_ms = int((time.time() - start) * 1000)
            columns = list(rows[0].keys()) if rows else []

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "elapsed_ms": elapsed_ms,
            }
        except Exception as e:
            logger.error(f"[Doris] Query failed: {e}")
            raise
        finally:
            conn.close()

    async def list_databases(self) -> list[str]:
        """List all databases in Doris."""
        conn = self._get_mysql_conn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES")
                return [row["Database"] for row in cursor.fetchall()]
        finally:
            conn.close()

    async def list_tables(self, database: str) -> list[dict]:
        """List tables in a Doris database with details."""
        conn = self._get_mysql_conn(database)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                result = []
                for row in tables:
                    table_name = list(row.values())[0]
                    cursor.execute(f"SHOW TABLE STATUS LIKE '{table_name}'")
                    status = cursor.fetchone() or {}
                    result.append({
                        "name": table_name,
                        "engine": status.get("Engine", ""),
                        "rows": status.get("Rows", 0),
                        "data_size": status.get("Data_length", 0),
                    })
                return result
        finally:
            conn.close()

    async def get_table_schema(self, database: str, table_name: str) -> list[dict]:
        """Get column definitions of a table."""
        conn = self._get_mysql_conn(database)
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"DESC {database}.{table_name}")
                return cursor.fetchall()
        finally:
            conn.close()

    async def close(self):
        """No persistent connection to close for pymysql."""
        pass
