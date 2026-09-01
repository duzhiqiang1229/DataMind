import unittest

from app.services.data_service import _cube_member_name, _qualify_cube_member


class DataServiceCubeMemberTests(unittest.TestCase):
    def test_qualifies_short_member(self):
        self.assertEqual(
            _qualify_cube_member("fee_cashflow_daily", "inflow_amount"),
            "fee_cashflow_daily.inflow_amount",
        )

    def test_preserves_qualified_member(self):
        self.assertEqual(
            _qualify_cube_member("fee_cashflow_daily", "fee_cashflow_daily.stat_date"),
            "fee_cashflow_daily.stat_date",
        )

    def test_extracts_member_name_for_validation(self):
        self.assertEqual(_cube_member_name("fee_cashflow_daily.comm_id"), "comm_id")
        self.assertEqual(_cube_member_name("comm_id"), "comm_id")


if __name__ == "__main__":
    unittest.main()
