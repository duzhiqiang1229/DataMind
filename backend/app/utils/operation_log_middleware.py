"""
Operation logging middleware.
Automatically records API operations to the operation_logs table.

Logs method, path, status code, user info, IP, and request body (truncated).
Excludes health checks and docs endpoints.
"""
import time
import json
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import select
from loguru import logger

from app.core.database import async_session
from app.core.security import decode_token
from app.models import OperationLog


# Paths to skip logging
SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class OperationLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs API operations to the database."""

    async def dispatch(self, request: Request, call_next):
        # Skip non-API paths and GET requests to reduce noise
        path = request.url.path
        if path in SKIP_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # Skip GET requests (read operations) to reduce log volume
        if request.method == "GET":
            return await call_next(request)

        # Capture request body before processing
        body = await request.body()
        body_text = body.decode("utf-8", errors="ignore")[:2000] if body else ""

        # Read Authorization header for user info
        auth_header = request.headers.get("Authorization", "")
        user_id = None
        username = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_token(token)
                user_id_str = payload.get("sub")
                username = payload.get("username")
                if user_id_str:
                    import uuid
                    user_id = uuid.UUID(user_id_str)
            except Exception:
                pass

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Process request
        start_time = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Determine module from path
        module = self._extract_module(path)

        # Determine action from method
        action_map = {
            "POST": "create",
            "PUT": "update",
            "DELETE": "delete",
            "PATCH": "patch",
        }
        action = action_map.get(request.method, request.method.lower())

        # Write to database (async, non-blocking on failure)
        try:
            async with async_session() as db:
                log = OperationLog(
                    user_id=user_id,
                    username=username,
                    module=module,
                    action=action,
                    target_type=module,
                    target_id=None,
                    description=f"{request.method} {path}",
                    request_method=request.method,
                    request_path=path,
                    request_body=body_text if body_text else None,
                    status_code=response.status_code,
                    ip_address=client_ip,
                )
                db.add(log)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to write operation log: {e}")

        return response

    def _extract_module(self, path: str) -> Optional[str]:
        """Extract module name from API path."""
        # /api/v1/datax-tasks/xxx -> datax
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            endpoint = parts[2]
            # Normalize module names
            module_map = {
                "auth": "auth",
                "users": "user",
                "roles": "role",
                "menus": "menu",
                "components": "component",
                "datasources": "datasource",
                "datax-tasks": "datax",
                "spark-tasks": "spark",
                "doris-query": "doris",
                "data-models": "model",
                "publish": "publish",
                "dashboard": "dashboard",
                "system": "system",
                "cube": "cube",
                "openmetadata": "openmetadata",
            }
            return module_map.get(endpoint, endpoint)
        return None
