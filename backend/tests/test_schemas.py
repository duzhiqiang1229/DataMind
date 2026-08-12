"""
Unit tests for Pydantic schemas and common models.

These tests validate request/response models and the common ResponseOK / PageResult
wrappers. No database or Redis required.
"""
import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest
from app.schemas.common import ResponseOK, PageResult
from app.schemas.data_model import DataModelCreate


class TestLoginRequest:
    def test_valid_login_request(self):
        req = LoginRequest(username="admin", password="admin123")
        assert req.username == "admin"
        assert req.password == "admin123"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="a", password="admin123")

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="12345")  # min 6

    def test_missing_fields(self):
        with pytest.raises(ValidationError):
            LoginRequest()


class TestTokenResponse:
    def test_valid_token_response(self):
        resp = TokenResponse(
            access_token="access",
            refresh_token="refresh",
            expires_in=7200,
        )
        assert resp.token_type == "bearer"
        assert resp.expires_in == 7200


class TestRefreshTokenRequest:
    def test_valid_refresh_request(self):
        req = RefreshTokenRequest(refresh_token="some-token")
        assert req.refresh_token == "some-token"


class TestResponseOK:
    def test_default_success(self):
        resp = ResponseOK()
        assert resp.code == 200
        assert resp.message == "success"
        assert resp.data is None

    def test_with_data(self):
        resp = ResponseOK(data={"key": "value"})
        assert resp.data == {"key": "value"}

    def test_error_response(self):
        resp = ResponseOK(code=401, message="Invalid credentials", data=None)
        assert resp.code == 401
        assert resp.message == "Invalid credentials"


class TestPageResult:
    def test_create_with_single_page(self):
        result = PageResult.create(
            items=["a", "b", "c"], total=3, page=1, page_size=10
        )
        assert result.total == 3
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 1

    def test_create_with_multiple_pages(self):
        result = PageResult.create(
            items=["a"], total=25, page=3, page_size=10
        )
        assert result.total_pages == 3

    def test_create_with_zero_items(self):
        result = PageResult.create(items=[], total=0, page=1, page_size=10)
        assert result.total_pages == 0


class TestDataModelCreate:
    def test_dim_layer_is_supported(self):
        model = DataModelCreate(
            model_name="客户维度",
            layer="dim",
            database="dim",
            table_name="dim_customer",
            data_domain="客户入住域",
            business_domain="客户档案维护",
            model_grain="每个客户一条记录",
            update_strategy="full_merge",
            source_tables=["ods_customer"],
        )
        assert model.layer == "dim"
        assert model.source_tables == ["ods_customer"]

    def test_unknown_layer_is_rejected(self):
        with pytest.raises(ValidationError):
            DataModelCreate(
                model_name="Bad layer",
                layer="stg",
                database="stg",
                table_name="bad_layer",
            )
