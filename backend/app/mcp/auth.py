"""Bearer-token authentication middleware for the internal MCP deployment."""
from app.core.database import async_session
from app.mcp.context import principal_context
from app.services.mcp_service import validate_token


class McpBearerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        authorization = headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            await self._reject(send, "Missing MCP bearer token")
            return
        raw_token = authorization.split(" ", 1)[1].strip()
        async with async_session() as db:
            principal = await validate_token(db, raw_token)
        if not principal:
            await self._reject(send, "Invalid, expired or revoked MCP token")
            return
        marker = principal_context.set(principal)
        try:
            await self.app(scope, receive, send)
        finally:
            principal_context.reset(marker)

    @staticmethod
    async def _reject(send, message: str):
        body = (f'{{"error":"invalid_token","error_description":"{message}"}}').encode()
        await send({
            "type": "http.response.start", "status": 401,
            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")],
        })
        await send({"type": "http.response.body", "body": body})
