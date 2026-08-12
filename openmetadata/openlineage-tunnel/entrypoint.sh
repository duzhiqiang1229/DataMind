#!/bin/sh
set -eu

# Docker Desktop bind mounts inherit permissive Windows ACLs. OpenSSH refuses
# such a key, so copy it into the container filesystem and lock it down first.
install -m 600 /run/ssh/openlineage_tunnel_ed25519 /tmp/openlineage_tunnel_ed25519

exec ssh -NT \
  -i /tmp/openlineage_tunnel_ed25519 \
  -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/tmp/known_hosts \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -R 127.0.0.1:18585:openlineage-relay:8587 \
  "${OPENLINEAGE_SSH_USER:-root}@${OPENLINEAGE_SSH_HOST:-192.168.1.4}"
