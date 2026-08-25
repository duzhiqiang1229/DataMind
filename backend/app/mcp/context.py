"""Per-request MCP caller identity."""
from contextvars import ContextVar


principal_context: ContextVar[dict | None] = ContextVar("mcp_principal", default=None)


def require_principal(required_scope: str | None = None) -> dict:
    principal = principal_context.get()
    if not principal:
        raise PermissionError("MCP authentication required")
    if required_scope and required_scope not in principal.get("scopes", set()):
        raise PermissionError(f"Missing MCP scope: {required_scope}")
    return principal
