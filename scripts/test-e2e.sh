#!/usr/bin/env bash
# Run Playwright e2e against a freshly-rebuilt Docker container with a wiped DB volume.
set -uo pipefail

cd "$(dirname "$0")/.."

cleanup() {
  echo "Stopping..."
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Resetting Docker state..."
docker compose down -v >/dev/null 2>&1 || true

echo "Building and starting..."
DEV_MODE=1 docker compose up --build -d

echo "Waiting for /api/health..."
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/health >/dev/null; then
    break
  fi
  sleep 1
done

pushd frontend >/dev/null
BASE_URL=http://localhost:8000 npm run test:e2e
status=$?
popd >/dev/null

exit "$status"
