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

if [[ -z "${API_IMAGE:-}" || -z "${CONSUMER_IMAGE:-}" ]]; then
  echo "missing API_IMAGE/CONSUMER_IMAGE in env file: $ENV_FILE"
  echo "run scripts/cloud/phase8/build_push_images.sh first"
  exit 1
fi

DEPLOY_API="${DEPLOY_API:-1}"
DEPLOY_CONSUMER="${DEPLOY_CONSUMER:-1}"
REV_SUFFIX="${REV_SUFFIX:-p8$(date +%H%M%S)}"

az config set extension.use_dynamic_install=yes_without_prompt >/dev/null
az account set --subscription "$AZ_SUBSCRIPTION_ID"

if [[ "$DEPLOY_API" == "1" ]]; then
  if az containerapp show --resource-group "$AZ_RESOURCE_GROUP" --name "$CA_API_NAME" >/dev/null 2>&1; then
    echo "[phase8] updating API app: $CA_API_NAME"
    az containerapp secret set \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_API_NAME" \
      --secrets \
        db-url="$DATABASE_URL" \
        kafka-sasl-password="$KAFKA_SASL_PASSWORD" \
        appinsights-conn="$APPINSIGHTS_CONNECTION_STRING" \
      >/dev/null

    az containerapp update \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_API_NAME" \
      --image "$API_IMAGE" \
      --revision-suffix "$REV_SUFFIX" \
      --cpu 0.5 \
      --memory 1.0Gi \
      --min-replicas 1 \
      --max-replicas 1 \
      --set-env-vars \
        APP_ENV=dev \
        LOG_LEVEL=INFO \
        SERVICE_NAME=tx-lookup-api \
        AUTH_MODE=disabled \
        DATABASE_URL=secretref:db-url \
        KAFKA_BROKERS="$KAFKA_BROKERS" \
        KAFKA_SECURITY_PROTOCOL="$KAFKA_SECURITY_PROTOCOL" \
        KAFKA_SASL_MECHANISM="$KAFKA_SASL_MECHANISM" \
        KAFKA_SASL_USERNAME="$KAFKA_SASL_USERNAME" \
        KAFKA_SASL_PASSWORD=secretref:kafka-sasl-password \
        APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-conn \
        DB_POOL_SIZE=5 \
        DB_MAX_OVERFLOW=10 \
        DB_POOL_TIMEOUT=30 \
        DB_POOL_RECYCLE=1800 \
      >/dev/null

    az containerapp ingress update \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_API_NAME" \
      --type external \
      --target-port 8000 \
      --transport http \
      >/dev/null
  else
    echo "[phase8] creating API app: $CA_API_NAME"
    az containerapp create \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_API_NAME" \
      --environment "$CA_ENV_NAME" \
      --image "$API_IMAGE" \
      --ingress external \
      --target-port 8000 \
      --transport http \
      --registry-server "$ACR_LOGIN_SERVER" \
      --registry-username "$ACR_USERNAME" \
      --registry-password "$ACR_PASSWORD" \
      --cpu 0.5 \
      --memory 1.0Gi \
      --min-replicas 1 \
      --max-replicas 1 \
      --secrets \
        db-url="$DATABASE_URL" \
        kafka-sasl-password="$KAFKA_SASL_PASSWORD" \
        appinsights-conn="$APPINSIGHTS_CONNECTION_STRING" \
      --env-vars \
        APP_ENV=dev \
        LOG_LEVEL=INFO \
        SERVICE_NAME=tx-lookup-api \
        AUTH_MODE=disabled \
        DATABASE_URL=secretref:db-url \
        KAFKA_BROKERS="$KAFKA_BROKERS" \
        KAFKA_SECURITY_PROTOCOL="$KAFKA_SECURITY_PROTOCOL" \
        KAFKA_SASL_MECHANISM="$KAFKA_SASL_MECHANISM" \
        KAFKA_SASL_USERNAME="$KAFKA_SASL_USERNAME" \
        KAFKA_SASL_PASSWORD=secretref:kafka-sasl-password \
        APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-conn \
        DB_POOL_SIZE=5 \
        DB_MAX_OVERFLOW=10 \
        DB_POOL_TIMEOUT=30 \
        DB_POOL_RECYCLE=1800 \
      >/dev/null
  fi
fi

if [[ "$DEPLOY_CONSUMER" == "1" ]]; then
  if az containerapp show --resource-group "$AZ_RESOURCE_GROUP" --name "$CA_CONSUMER_NAME" >/dev/null 2>&1; then
    echo "[phase8] updating Consumer app: $CA_CONSUMER_NAME"
    az containerapp secret set \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_CONSUMER_NAME" \
      --secrets \
        db-url="$DATABASE_URL" \
        kafka-sasl-password="$KAFKA_SASL_PASSWORD" \
        appinsights-conn="$APPINSIGHTS_CONNECTION_STRING" \
      >/dev/null

    az containerapp update \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_CONSUMER_NAME" \
      --image "$CONSUMER_IMAGE" \
      --revision-suffix "$REV_SUFFIX" \
      --cpu 0.5 \
      --memory 1.0Gi \
      --min-replicas 1 \
      --max-replicas 1 \
      --set-env-vars \
        APP_ENV=dev \
        LOG_LEVEL=INFO \
        SERVICE_NAME=tx-lookup-consumer \
        AUTH_MODE=disabled \
        DATABASE_URL=secretref:db-url \
        KAFKA_BROKERS="$KAFKA_BROKERS" \
        KAFKA_SECURITY_PROTOCOL="$KAFKA_SECURITY_PROTOCOL" \
        KAFKA_SASL_MECHANISM="$KAFKA_SASL_MECHANISM" \
        KAFKA_SASL_USERNAME="$KAFKA_SASL_USERNAME" \
        KAFKA_SASL_PASSWORD=secretref:kafka-sasl-password \
        KAFKA_GROUP_ID="$EH_CONSUMER_GROUP" \
        LEDGER_TOPIC="$EH_HUB_LEDGER" \
        PAYMENT_ORDER_TOPIC="$EH_HUB_PAYMENT" \
        CONSUMER_OFFSET_RESET=earliest \
        DLQ_PATH=/tmp/dlq/failed_events.jsonl \
        APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-conn \
        METRICS_HOST=0.0.0.0 \
        METRICS_PORT=9108 \
      >/dev/null
  else
    echo "[phase8] creating Consumer app: $CA_CONSUMER_NAME"
    az containerapp create \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --name "$CA_CONSUMER_NAME" \
      --environment "$CA_ENV_NAME" \
      --image "$CONSUMER_IMAGE" \
      --registry-server "$ACR_LOGIN_SERVER" \
      --registry-username "$ACR_USERNAME" \
      --registry-password "$ACR_PASSWORD" \
      --cpu 0.5 \
      --memory 1.0Gi \
      --min-replicas 1 \
      --max-replicas 1 \
      --secrets \
        db-url="$DATABASE_URL" \
        kafka-sasl-password="$KAFKA_SASL_PASSWORD" \
        appinsights-conn="$APPINSIGHTS_CONNECTION_STRING" \
      --env-vars \
        APP_ENV=dev \
        LOG_LEVEL=INFO \
        SERVICE_NAME=tx-lookup-consumer \
        AUTH_MODE=disabled \
        DATABASE_URL=secretref:db-url \
        KAFKA_BROKERS="$KAFKA_BROKERS" \
        KAFKA_SECURITY_PROTOCOL="$KAFKA_SECURITY_PROTOCOL" \
        KAFKA_SASL_MECHANISM="$KAFKA_SASL_MECHANISM" \
        KAFKA_SASL_USERNAME="$KAFKA_SASL_USERNAME" \
        KAFKA_SASL_PASSWORD=secretref:kafka-sasl-password \
        KAFKA_GROUP_ID="$EH_CONSUMER_GROUP" \
        LEDGER_TOPIC="$EH_HUB_LEDGER" \
        PAYMENT_ORDER_TOPIC="$EH_HUB_PAYMENT" \
        CONSUMER_OFFSET_RESET=earliest \
        DLQ_PATH=/tmp/dlq/failed_events.jsonl \
        APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-conn \
        METRICS_HOST=0.0.0.0 \
        METRICS_PORT=9108 \
      >/dev/null
  fi
fi

if [[ "$DEPLOY_API" == "1" ]]; then
  API_FQDN="$(az containerapp show --resource-group "$AZ_RESOURCE_GROUP" --name "$CA_API_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
  API_BASE_URL="https://${API_FQDN}"
  {
    printf "API_FQDN=%q\n" "$API_FQDN"
    printf "API_BASE_URL=%q\n" "$API_BASE_URL"
  } >>"$ENV_FILE"
  echo "[phase8] API URL: $API_BASE_URL"
fi

echo "[phase8] deploy complete"
