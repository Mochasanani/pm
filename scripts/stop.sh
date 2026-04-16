#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Stopping Kanban Studio..."
docker compose down
echo "Kanban Studio stopped."
