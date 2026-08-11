"""SQL safety helpers for user-submitted read-only queries."""

import re

import sqlparse
from sqlparse.tokens import Comment, DML, Keyword


_READ_ONLY_TYPES = {"SELECT", "SHOW", "DESC", "DESCRIBE"}
_SIDE_EFFECT_PATTERNS = (
    re.compile(r"\bINTO\s+(?:OUTFILE|DUMPFILE)\b", re.IGNORECASE),
    re.compile(r"\bFOR\s+(?:UPDATE|SHARE)\b", re.IGNORECASE),
    re.compile(r"\bLOCK\s+IN\s+SHARE\s+MODE\b", re.IGNORECASE),
)


def _reject_select_side_effects(sql: str) -> None:
    """Reject SELECT variants that write files or acquire row locks."""
    without_comments = sqlparse.format(sql, strip_comments=True)
    if any(pattern.search(without_comments) for pattern in _SIDE_EFFECT_PATTERNS):
        raise ValueError("File-writing and locking SELECT variants are not allowed")


def validate_read_only_sql(sql: str, *, allow_with: bool = True) -> str:
    """Return normalized SQL when it is exactly one read-only statement.

    Prefix checks are insufficient because inputs such as
    ``SELECT 1; DROP TABLE ...`` and ``WITH ... DELETE ...`` still start with an
    allowed word. sqlparse identifies the effective DML verb and also lets us
    reject multiple statements before handing anything to a database driver.
    """
    statements = [statement for statement in sqlparse.parse(sql) if str(statement).strip()]
    if len(statements) != 1:
        raise ValueError("Only one read-only SQL statement is allowed")

    statement = statements[0]
    statement_type = statement.get_type().upper()
    if statement_type == "SELECT":
        normalized = str(statement).strip().rstrip(";").strip()
        _reject_select_side_effects(normalized)
        return normalized

    first_keyword = ""
    for token in statement.flatten():
        if token.is_whitespace or token.ttype in Comment:
            continue
        if token.ttype in Keyword or token.ttype in DML:
            first_keyword = token.normalized.upper()
        break

    allowed = {"SHOW", "DESC", "DESCRIBE"}
    if allow_with:
        allowed.add("WITH")
    if first_keyword not in allowed:
        raise ValueError("Only SELECT/SHOW/DESC/WITH queries are allowed")

    # A WITH statement must ultimately be a SELECT. Newer sqlparse versions
    # report that as SELECT; reject UNKNOWN rather than guessing its intent.
    if first_keyword == "WITH" and statement_type != "SELECT":
        raise ValueError("WITH queries must end in SELECT")
    return str(statement).strip().rstrip(";").strip()
