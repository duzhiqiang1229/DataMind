"""Export the OpenMetadata bot JWT as a protected nginx include file."""

import asyncio
import os

from app.core.database import async_session
from app.services.component_service import _load_config


async def main() -> None:
    async with async_session() as db:
        config = await _load_config(db, "openmetadata")
    token = ((config or {}).get("credentials") or {}).get("jwt_token")
    if not token or str(token).count(".") != 2:
        raise RuntimeError("OpenMetadata component has no usable bot JWT")
    target = os.environ.get(
        "OPENLINEAGE_RELAY_AUTH_PATH", "/tmp/openlineage-auth.conf"
    )
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(f'proxy_set_header Authorization "Bearer {token}";\n')
    os.chmod(target, 0o600)
    print(target)


if __name__ == "__main__":
    asyncio.run(main())
