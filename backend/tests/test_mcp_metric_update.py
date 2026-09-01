import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.mcp import server


class McpMetricUpdateTests(unittest.TestCase):
    def test_tool_catalog_exposes_metric_update_as_draft_operation(self):
        catalog = asyncio.run(server.build_tool_catalog())
        tool = next(item for item in catalog["items"] if item["name"] == "update_metric_definition_draft")

        self.assertEqual(tool["module"], "指标建设")
        self.assertEqual(tool["scope"], "metrics:draft")
        self.assertEqual(tool["risk_level"], "medium")
        self.assertFalse(tool["confirmation_required"])
        self.assertIn("更新现有指标定义", tool["description"])

    def test_update_metric_definition_stages_only_requested_changes(self):
        captured = {}

        async def run_tool(name, scope, arguments, operation):
            captured.update(name=name, scope=scope, arguments=arguments)
            return await operation("db", {"client_id": "client"})

        with (
            patch.object(server, "_run_tool", side_effect=run_tool),
            patch.object(
                server.mcp_service,
                "add_metric_definition_update_item",
                new=AsyncMock(return_value={"status": "draft", "action": "update"}),
            ) as stage_update,
        ):
            result = asyncio.run(server.update_metric_definition_draft(
                change_set_id="d347e3ca-8668-46c0-a78c-ad1b0cc2d79a",
                metric_code="net_cashflow_amount",
                metric_name="净现金流金额",
                unit="元",
                clear_fields=["description"],
            ))

        self.assertEqual(result["action"], "update")
        self.assertEqual(captured["name"], "update_metric_definition_draft")
        self.assertEqual(captured["scope"], "metrics:draft")
        self.assertNotIn("cube_name", captured["arguments"])
        stage_update.assert_awaited_once()
        call_args = stage_update.await_args.args
        self.assertEqual(call_args[3], "net_cashflow_amount")
        self.assertEqual(call_args[4], {"metric_name": "净现金流金额", "unit": "元"})
        self.assertEqual(call_args[5], ["description"])


if __name__ == "__main__":
    unittest.main()
