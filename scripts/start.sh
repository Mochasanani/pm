#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker &>/dev/null; then
  echo "Error: docker is not installed." >&2
  exit 1
fi

echo "Building and starting Kanban Studio..."
docker compose up --build -d
echo "Kanban Studio is running at http://localhost:8000"
