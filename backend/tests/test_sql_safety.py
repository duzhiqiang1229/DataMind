"""Read-only SQL validation tests."""

import pytest

from app.utils.sql_safety import validate_read_only_sql


@pytest.mark.parametrize("sql", [
    "SELECT * FROM users",
    "SHOW TABLES",
    "DESC users",
    "WITH recent AS (SELECT 1 AS id) SELECT * FROM recent",
])
def test_accepts_single_read_only_statement(sql):
    assert validate_read_only_sql(sql)


@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE users",
    "WITH victim AS (SELECT 1) DELETE FROM users",
    "UPDATE users SET status = 'disabled'",
    "/* misleading comment */ DELETE FROM users",
    "SELECT * FROM users INTO OUTFILE '/tmp/users.csv'",
    "SELECT * FROM users INTO DUMPFILE '/tmp/users.bin'",
    "SELECT * FROM users FOR UPDATE",
    "SELECT * FROM users LOCK IN SHARE MODE",
])
def test_rejects_writes_and_multiple_statements(sql):
    with pytest.raises(ValueError):
        validate_read_only_sql(sql)
