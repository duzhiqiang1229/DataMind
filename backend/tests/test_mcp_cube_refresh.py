import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.mcp import server


class McpCubeRefreshTests(unittest.TestCase):
    def test_tool_catalog_marks_cube_refresh_as_confirmed_high_risk_execution(self):
        catalog = asyncio.run(server.build_tool_catalog())
        tool = next(item for item in catalog["items"] if item["name"] == "refresh_cube")

        self.assertEqual(tool["module"], "指标建设")
        self.assertEqual(tool["scope"], "metrics:execute")
        self.assertEqual(tool["risk_level"], "high")
        self.assertTrue(tool["confirmation_required"])
        self.assertIn("人工确认", tool["description"])

    def test_refresh_cube_reuses_existing_cube_service(self):
        captured = {}

        async def run_tool(name, scope, arguments, operation):
            captured.update(name=name, scope=scope, arguments=arguments)
            return await operation(None, {"username": "agent"})

        with (
            patch.object(server, "_run_tool", side_effect=run_tool),
            patch.object(
                server.cube_model_service,
                "refresh_cube",
                new=AsyncMock(return_value={"ok": True, "message": "Cube 已重启，模型已生效"}),
            ) as refresh,
        ):
            result = asyncio.run(server.refresh_cube(user_confirmation=True))

        self.assertTrue(result["ok"])
        self.assertEqual(captured["name"], "refresh_cube")
        self.assertEqual(captured["scope"], "metrics:execute")
        self.assertEqual(captured["arguments"], {"user_confirmation": True})
        refresh.assert_awaited_once_with()

    def test_refresh_cube_rejects_missing_confirmation(self):
        async def run_tool(name, scope, arguments, operation):
            return await operation(None, {"username": "agent"})

        with (
            patch.object(server, "_run_tool", side_effect=run_tool),
            patch.object(server.cube_model_service, "refresh_cube", new=AsyncMock()) as refresh,
        ):
            with self.assertRaisesRegex(ValueError, "Explicit user confirmation"):
                asyncio.run(server.refresh_cube())

        refresh.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
