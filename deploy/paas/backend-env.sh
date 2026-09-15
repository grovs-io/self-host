#!/usr/bin/env bash
# Sourced into the commands embedded in Railway/Render configuration.
# No files from this repository need to be present in the application image.
set -eu
: "${SERVER_HOST:?Set your app domain}"
: "${DOMAIN_LIVE:?Set your production links domain}"
: "${DOMAIN_TEST:?Set your test links domain}"
: "${AWS_S3_KEY_ID:?Set object storage credentials}"
: "${AWS_S3_ACCESS_KEY:?Set object storage credentials}"
: "${AWS_S3_REGION:?Set your bucket region}"
: "${AWS_S3_BUCKET:?Set your bucket name}"
export ACTIVE_STORAGE_SERVICE=amazon
export SERVER_HOST_PROTOCOL=https:// REACT_HOST_PROTOCOL=https://
export REACT_HOST="dashboard.$SERVER_HOST"
export API_HOST="api.$SERVER_HOST" SDK_HOST="sdk.$SERVER_HOST"
export DASHBOARD_HOST="$REACT_HOST" MCP_HOST="mcp.$SERVER_HOST" GO_HOST="go.$SERVER_HOST"
export PREVIEW_HOST="preview.$SERVER_HOST"
export LINKS_PROD_HOST="links.$DOMAIN_LIVE" LINKS_TEST_HOST="links.$DOMAIN_TEST"
export PREVIEW_BASE_URL="https://preview.$SERVER_HOST"
export MCP_CONSENT_URL="https://dashboard.$SERVER_HOST/mcp/authorize"
export S3_ASSET_PREFIX="https://api.$SERVER_HOST"
encode_password() {
  ruby -ruri -e 'print URI.encode_www_form_component(ENV.fetch(ARGV.fetch(0))).gsub("+", "%20")' "$1"
}
if [ -z "${DATABASE_URL:-}" ]; then
  : "${POSTGRES_HOST:?Set the private PostgreSQL host}"
  DATABASE_URL="postgres://grovs:$(encode_password POSTGRES_PASSWORD)@$POSTGRES_HOST:5432/grovs_production"
  export DATABASE_URL
fi
if [ -z "${REDIS_URL:-}" ]; then
  : "${REDIS_HOST:?Set the private Redis host}"
  REDIS_URL="redis://:$(encode_password REDIS_PASSWORD)@$REDIS_HOST:6379/0"
  export REDIS_URL
fi
if [ -z "${CLICKHOUSE_URL:-}" ]; then
  : "${CLICKHOUSE_HOST:?Set the private ClickHouse host}"
  : "${CLICKHOUSE_PASSWORD:?Set the ClickHouse password}"
  ENCODED_PASSWORD=$(encode_password CLICKHOUSE_PASSWORD)
  export CLICKHOUSE_URL="http://grovs:$ENCODED_PASSWORD@$CLICKHOUSE_HOST:8123"
fi

wait_for_http() {
  local attempt
  for ((attempt=0; attempt<120; attempt++)); do
    if curl --fail --silent --max-time 5 "$1" >/dev/null; then return 0; fi
    sleep 5
  done
  echo "Dependency did not become healthy within the startup window." >&2
  return 1
}
