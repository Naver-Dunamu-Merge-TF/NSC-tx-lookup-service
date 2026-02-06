#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${PHASE8_ENV_FILE:-$ROOT_DIR/.env/phase8_cloud_test.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file: $ENV_FILE"
  echo "run scripts/cloud/phase8/provision_resources.sh first"
  exit 1
fi

source "$ENV_FILE"
export DATABASE_URL

echo "[phase8] running alembic migration against cloud DB"
python -m alembic upgrade head
echo "[phase8] migration complete"
