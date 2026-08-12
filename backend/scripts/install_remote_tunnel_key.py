"""Authorize the dedicated OpenLineage reverse-tunnel key on business Airflow."""

import asyncio
import os

import paramiko

from app.core.database import async_session
from app.services.airflow_service import _airflow_ssh_config


async def main() -> None:
    public_key_path = os.environ.get(
        "TUNNEL_PUBLIC_KEY_PATH", "/tmp/openlineage_tunnel_ed25519.pub"
    )
    with open(public_key_path, encoding="utf-8") as handle:
        public_key = handle.read().strip()
    if not public_key.startswith("ssh-ed25519 "):
        raise ValueError("Expected an Ed25519 OpenSSH public key")

    async with async_session() as db:
        cfg = await _airflow_ssh_config(db)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        cfg["host"], port=cfg["port"], username=cfg["user"],
        password=cfg["password"], timeout=15,
    )
    try:
        with client.open_sftp() as sftp:
            try:
                sftp.stat("/root/.ssh")
            except FileNotFoundError:
                sftp.mkdir("/root/.ssh", mode=0o700)
            path = "/root/.ssh/authorized_keys"
            try:
                with sftp.open(path, "r") as handle:
                    existing = handle.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                existing = ""
            if public_key not in existing.splitlines():
                with sftp.open(path, "a") as handle:
                    handle.write(("" if existing.endswith("\n") or not existing else "\n") + public_key + "\n")
            sftp.chmod(path, 0o600)
        print("OpenLineage tunnel key authorized")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
