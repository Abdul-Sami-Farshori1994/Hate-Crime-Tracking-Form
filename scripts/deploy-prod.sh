#!/usr/bin/env bash
# Production deploy — works with docker-compose (v1) and docker compose (v2 plugin).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Error: install Docker Compose (docker-compose or docker compose plugin)." >&2
  exit 1
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${SECRET_KEY:?Set SECRET_KEY (e.g. export SECRET_KEY=\$(openssl rand -hex 32))}"
: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env or the environment}"

export ENVIRONMENT="${ENVIRONMENT:-production}"
export ALLOW_DEFAULT_USER_SEED="${ALLOW_DEFAULT_USER_SEED:-false}"

echo "Using: ${COMPOSE[*]}"
"${COMPOSE[@]}" -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "Deployed. Web UI: http://$(hostname -I 2>/dev/null | awk '{print $1}'):8080"
echo "Logs: ${COMPOSE[*]} logs -f api"
