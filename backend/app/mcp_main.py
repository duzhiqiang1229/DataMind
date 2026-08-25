"""ASGI entry point for the DataMind MCP service."""
from app.mcp.server import app

__all__ = ["app"]
