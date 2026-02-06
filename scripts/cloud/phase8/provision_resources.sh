#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${PHASE8_ENV_FILE:-$ROOT_DIR/.env/phase8_cloud_test.env}"
mkdir -p "$(dirname "$ENV_FILE")"

az config set extension.use_dynamic_install=yes_without_prompt >/dev/null
az config set extension.dynamic_install_allow_preview=false >/dev/null

AZ_SUBSCRIPTION_ID="${AZ_SUBSCRIPTION_ID:-$(az account show --query id -o tsv)}"
AZ_RESOURCE_GROUP="${AZ_RESOURCE_GROUP:-2dt-final-team4}"
AZ_LOCATION="${AZ_LOCATION:-koreacentral}"
AZ_OWNER="${AZ_OWNER:-2dt026}"
AZ_ENV_NAME="${AZ_ENV_NAME:-test}"
AZ_TTL="${AZ_TTL:-2026-02-28}"

EH_NAMESPACE="${EH_NAMESPACE:-team4-txlookup-${AZ_OWNER}-${AZ_ENV_NAME}}"
EH_HUB_LEDGER="${EH_HUB_LEDGER:-ledger.entry.upserted}"
EH_HUB_PAYMENT="${EH_HUB_PAYMENT:-payment.order.upserted}"
EH_CONSUMER_GROUP="${EH_CONSUMER_GROUP:-bo-sync-${AZ_ENV_NAME}-${AZ_OWNER}-v1}"
EH_PARTITION_COUNT="${EH_PARTITION_COUNT:-2}"
EH_RETENTION_HOURS="${EH_RETENTION_HOURS:-72}"

PG_SERVER="${PG_SERVER:-team4-txlookup-pg-${AZ_OWNER}-${AZ_ENV_NAME}}"
PG_DB_NAME="${PG_DB_NAME:-bo}"
PG_ADMIN_USER="${PG_ADMIN_USER:-boadmin}"
if [[ -z "${PG_ADMIN_PASSWORD:-}" ]]; then
  PG_ADMIN_PASSWORD="P8Test!${AZ_OWNER}$(date +%s)Aa"
fi

ACR_NAME="${ACR_NAME:-team4txlookup${AZ_OWNER}${AZ_ENV_NAME}}"

CA_ENV_NAME="${CA_ENV_NAME:-team4-tx-caenv-${AZ_OWNER}-t}"
CA_API_NAME="${CA_API_NAME:-team4-tx-api-${AZ_OWNER}-t}"
CA_CONSUMER_NAME="${CA_CONSUMER_NAME:-team4-tx-con-${AZ_OWNER}-t}"

LAW_NAME="${LAW_NAME:-team4-txlookup-law-${AZ_OWNER}-${AZ_ENV_NAME}}"
APPINSIGHTS_NAME="${APPINSIGHTS_NAME:-team4-txlookup-ai-${AZ_OWNER}-${AZ_ENV_NAME}}"

TAGS=(
  "env=${AZ_ENV_NAME}"
  "owner=${AZ_OWNER}"
  "project=txlookup"
  "ttl=${AZ_TTL}"
)

echo "[phase8] subscription=${AZ_SUBSCRIPTION_ID} rg=${AZ_RESOURCE_GROUP} location=${AZ_LOCATION}"
az account set --subscription "$AZ_SUBSCRIPTION_ID"
az group create \
  --name "$AZ_RESOURCE_GROUP" \
  --location "$AZ_LOCATION" \
  --tags "${TAGS[@]}" \
  >/dev/null

if ! az monitor log-analytics workspace show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --workspace-name "$LAW_NAME" \
  >/dev/null 2>&1; then
  echo "[phase8] creating Log Analytics workspace: $LAW_NAME"
  az monitor log-analytics workspace create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --workspace-name "$LAW_NAME" \
    --location "$AZ_LOCATION" \
    --tags "${TAGS[@]}" \
    >/dev/null
fi

LAW_CUSTOMER_ID="$(az monitor log-analytics workspace show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --workspace-name "$LAW_NAME" \
  --query customerId -o tsv)"
LAW_SHARED_KEY="$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --workspace-name "$LAW_NAME" \
  --query primarySharedKey -o tsv)"
LAW_RESOURCE_ID="$(az monitor log-analytics workspace show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --workspace-name "$LAW_NAME" \
  --query id -o tsv)"

if ! az monitor app-insights component show \
  --app "$APPINSIGHTS_NAME" \
  --resource-group "$AZ_RESOURCE_GROUP" \
  >/dev/null 2>&1; then
  echo "[phase8] creating Application Insights: $APPINSIGHTS_NAME"
  az monitor app-insights component create \
    --app "$APPINSIGHTS_NAME" \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --location "$AZ_LOCATION" \
    --application-type web \
    --workspace "$LAW_RESOURCE_ID" \
    --ingestion-access Enabled \
    --query-access Enabled \
    --tags "${TAGS[@]}" \
    >/dev/null
fi

APPINSIGHTS_CONNECTION_STRING="$(az monitor app-insights component show \
  --app "$APPINSIGHTS_NAME" \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --query connectionString -o tsv)"

if ! az eventhubs namespace show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$EH_NAMESPACE" \
  >/dev/null 2>&1; then
  echo "[phase8] creating Event Hubs namespace: $EH_NAMESPACE"
  az eventhubs namespace create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$EH_NAMESPACE" \
    --location "$AZ_LOCATION" \
    --sku Standard \
    --enable-kafka true \
    --public-network Enabled \
    --tags "${TAGS[@]}" \
    >/dev/null
fi

for hub in "$EH_HUB_LEDGER" "$EH_HUB_PAYMENT"; do
  if ! az eventhubs eventhub show \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --namespace-name "$EH_NAMESPACE" \
    --name "$hub" \
    >/dev/null 2>&1; then
    echo "[phase8] creating event hub: $hub"
    az eventhubs eventhub create \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --namespace-name "$EH_NAMESPACE" \
      --name "$hub" \
      --partition-count "$EH_PARTITION_COUNT" \
      --cleanup-policy Delete \
      --retention-time "$EH_RETENTION_HOURS" \
      >/dev/null
  fi

  if ! az eventhubs eventhub consumer-group show \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --namespace-name "$EH_NAMESPACE" \
    --eventhub-name "$hub" \
    --name "$EH_CONSUMER_GROUP" \
    >/dev/null 2>&1; then
    az eventhubs eventhub consumer-group create \
      --resource-group "$AZ_RESOURCE_GROUP" \
      --namespace-name "$EH_NAMESPACE" \
      --eventhub-name "$hub" \
      --name "$EH_CONSUMER_GROUP" \
      >/dev/null
  fi
done

EH_NAMESPACE_CONNECTION_STRING="$(az eventhubs namespace authorization-rule keys list \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --namespace-name "$EH_NAMESPACE" \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv)"
KAFKA_BROKERS="${EH_NAMESPACE}.servicebus.windows.net:9093"

if ! az postgres flexible-server show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$PG_SERVER" \
  >/dev/null 2>&1; then
  echo "[phase8] creating PostgreSQL flexible server: $PG_SERVER"
  az postgres flexible-server create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$PG_SERVER" \
    --location "$AZ_LOCATION" \
    --admin-user "$PG_ADMIN_USER" \
    --admin-password "$PG_ADMIN_PASSWORD" \
    --tier Burstable \
    --sku-name Standard_B1ms \
    --storage-size 32 \
    --version 16 \
    --public-access All \
    --yes \
    --tags "${TAGS[@]}" \
    >/dev/null
else
  az postgres flexible-server update \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$PG_SERVER" \
    --admin-password "$PG_ADMIN_PASSWORD" \
    --public-access Enabled \
    --yes \
    >/dev/null
fi

az postgres flexible-server firewall-rule create \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$PG_SERVER" \
  --rule-name AllowAllInternet \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255 \
  >/dev/null

if ! az postgres flexible-server db show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --server-name "$PG_SERVER" \
  --database-name "$PG_DB_NAME" \
  >/dev/null 2>&1; then
  az postgres flexible-server db create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --server-name "$PG_SERVER" \
    --database-name "$PG_DB_NAME" \
    >/dev/null
fi

PG_FQDN="$(az postgres flexible-server show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$PG_SERVER" \
  --query fullyQualifiedDomainName -o tsv)"
DATABASE_URL="postgresql+psycopg://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_FQDN}:5432/${PG_DB_NAME}?sslmode=require"

if ! az acr show --resource-group "$AZ_RESOURCE_GROUP" --name "$ACR_NAME" >/dev/null 2>&1; then
  echo "[phase8] creating ACR: $ACR_NAME"
  az acr create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --location "$AZ_LOCATION" \
    --sku Basic \
    --admin-enabled true \
    --tags "${TAGS[@]}" \
    >/dev/null
else
  az acr update \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --admin-enabled true \
    >/dev/null
fi

ACR_LOGIN_SERVER="$(az acr show --resource-group "$AZ_RESOURCE_GROUP" --name "$ACR_NAME" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show --resource-group "$AZ_RESOURCE_GROUP" --name "$ACR_NAME" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --resource-group "$AZ_RESOURCE_GROUP" --name "$ACR_NAME" --query passwords[0].value -o tsv)"

if ! az containerapp env show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$CA_ENV_NAME" \
  >/dev/null 2>&1; then
  echo "[phase8] creating Container Apps environment: $CA_ENV_NAME"
  az containerapp env create \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$CA_ENV_NAME" \
    --location "$AZ_LOCATION" \
    --logs-workspace-id "$LAW_CUSTOMER_ID" \
    --logs-workspace-key "$LAW_SHARED_KEY" \
    --tags "${TAGS[@]}" \
    >/dev/null
fi

tmp_file="${ENV_FILE}.tmp"
{
  echo "# generated by scripts/cloud/phase8/provision_resources.sh"
  printf "AZ_SUBSCRIPTION_ID=%q\n" "$AZ_SUBSCRIPTION_ID"
  printf "AZ_RESOURCE_GROUP=%q\n" "$AZ_RESOURCE_GROUP"
  printf "AZ_LOCATION=%q\n" "$AZ_LOCATION"
  printf "AZ_OWNER=%q\n" "$AZ_OWNER"
  printf "AZ_ENV_NAME=%q\n" "$AZ_ENV_NAME"
  printf "AZ_TTL=%q\n" "$AZ_TTL"

  printf "EH_NAMESPACE=%q\n" "$EH_NAMESPACE"
  printf "EH_HUB_LEDGER=%q\n" "$EH_HUB_LEDGER"
  printf "EH_HUB_PAYMENT=%q\n" "$EH_HUB_PAYMENT"
  printf "EH_CONSUMER_GROUP=%q\n" "$EH_CONSUMER_GROUP"
  printf "KAFKA_BROKERS=%q\n" "$KAFKA_BROKERS"
  printf "KAFKA_SECURITY_PROTOCOL=%q\n" "SASL_SSL"
  printf "KAFKA_SASL_MECHANISM=%q\n" "PLAIN"
  printf "KAFKA_SASL_USERNAME=%q\n" "\$ConnectionString"
  printf "KAFKA_SASL_PASSWORD=%q\n" "$EH_NAMESPACE_CONNECTION_STRING"

  printf "PG_SERVER=%q\n" "$PG_SERVER"
  printf "PG_DB_NAME=%q\n" "$PG_DB_NAME"
  printf "PG_ADMIN_USER=%q\n" "$PG_ADMIN_USER"
  printf "PG_ADMIN_PASSWORD=%q\n" "$PG_ADMIN_PASSWORD"
  printf "PG_FQDN=%q\n" "$PG_FQDN"
  printf "DATABASE_URL=%q\n" "$DATABASE_URL"

  printf "ACR_NAME=%q\n" "$ACR_NAME"
  printf "ACR_LOGIN_SERVER=%q\n" "$ACR_LOGIN_SERVER"
  printf "ACR_USERNAME=%q\n" "$ACR_USERNAME"
  printf "ACR_PASSWORD=%q\n" "$ACR_PASSWORD"

  printf "CA_ENV_NAME=%q\n" "$CA_ENV_NAME"
  printf "CA_API_NAME=%q\n" "$CA_API_NAME"
  printf "CA_CONSUMER_NAME=%q\n" "$CA_CONSUMER_NAME"

  printf "LAW_NAME=%q\n" "$LAW_NAME"
  printf "LAW_CUSTOMER_ID=%q\n" "$LAW_CUSTOMER_ID"
  printf "APPINSIGHTS_NAME=%q\n" "$APPINSIGHTS_NAME"
  printf "APPINSIGHTS_CONNECTION_STRING=%q\n" "$APPINSIGHTS_CONNECTION_STRING"
} >"$tmp_file"
mv "$tmp_file" "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "[phase8] provision complete"
echo "[phase8] runtime env file: $ENV_FILE"
