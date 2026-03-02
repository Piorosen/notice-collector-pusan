#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Stop containers and remove volumes"
docker compose down -v --remove-orphans

echo "[2/4] Remove storage cache"
rm -rf storage
mkdir -p storage/attachments storage/images

echo "[3/4] Rebuild and start services"
docker compose up -d --build

echo "[4/4] Wait a moment for startup"
sleep 5
curl -fsS http://localhost:8000/health >/dev/null
echo "Reset complete"
