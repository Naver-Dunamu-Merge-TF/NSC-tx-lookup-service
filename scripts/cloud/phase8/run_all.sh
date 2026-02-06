#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${PHASE8_ENV_FILE:-$ROOT_DIR/.env/phase8_cloud_test.env}"

"$ROOT_DIR/scripts/cloud/phase8/provision_resources.sh"
"$ROOT_DIR/scripts/cloud/phase8/build_push_images.sh"
"$ROOT_DIR/scripts/cloud/phase8/run_db_migrations.sh"
"$ROOT_DIR/scripts/cloud/phase8/deploy_apps.sh"
"$ROOT_DIR/scripts/cloud/phase8/run_smoke.sh"
"$ROOT_DIR/scripts/cloud/phase8/destroy_recreate_check.sh"

echo "[phase8] completed end-to-end. env file: $ENV_FILE"
