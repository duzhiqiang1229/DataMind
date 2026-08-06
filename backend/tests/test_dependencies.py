"""
Unit tests for app.core.dependencies: PaginationParams logic.

No database or Redis required.
"""
import pytest

from app.core.dependencies import PaginationParams


class TestPaginationParams:
    def test_default_values(self):
        p = PaginationParams(page=1, page_size=20)
        assert p.page == 1
        assert p.page_size == 20
        assert p.offset == 0

    def test_offset_calculation_page_2(self):
        p = PaginationParams(page=2, page_size=20)
        assert p.offset == 20

    def test_offset_calculation_page_3_size_15(self):
        p = PaginationParams(page=3, page_size=15)
        assert p.offset == 30

    def test_offset_first_page_is_zero(self):
        p = PaginationParams(page=1, page_size=50)
        assert p.offset == 0

    def test_offset_large_page(self):
        p = PaginationParams(page=10, page_size=25)
        assert p.offset == 225
