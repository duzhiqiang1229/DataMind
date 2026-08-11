"""Cube client authentication tests."""
import httpx
import jwt
import pytest

from app.integrations.cube_client import CubeClient


@pytest.mark.asyncio
async def test_cube_client_signs_each_request_with_api_secret():
    secret = "cube-api-secret-for-unit-tests-123456"
    captured_authorization = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_authorization
        captured_authorization = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"cubes": []})

    client = CubeClient({"base_url": "http://cube:4000", "api_secret": secret})
    client._client = httpx.AsyncClient(
        base_url="http://cube:4000",
        transport=httpx.MockTransport(handler),
    )

    try:
        result = await client.get_meta()
    finally:
        await client.close()

    assert result == {"cubes": []}
    assert captured_authorization.startswith("Bearer ")
    token = captured_authorization.removeprefix("Bearer ")
    claims = jwt.decode(token, secret, algorithms=["HS256"])
    assert claims["sub"] == "datamind-backend"
    assert claims["exp"] > claims["iat"]
