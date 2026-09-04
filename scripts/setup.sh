#!/usr/bin/env bash
# Create .env with strong secrets and your domains. Safe to re-run: keeps an existing .env.
# Non-interactive: GROVS_DOMAIN=example.com GROVS_ADMIN_EMAIL=you@example.com ./scripts/setup.sh  (GROVS_TEST_DOMAIN optional)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists, keeping it (delete it to regenerate)."
  exit 0
fi
cp .env.example .env

rnd() { openssl rand -hex "$1"; }
set_env() {
  awk -v k="$1" -v v="$2" 'BEGIN{FS="="} $1==k{print k"="v; next} {print}' .env > .env.tmp && mv .env.tmp .env
}
ask() {
  local var="$1" prompt="$2" default="${3:-}" value
  if [ -n "${!var:-}" ]; then return; fi
  if [ -t 0 ]; then
    read -r -p "$prompt${default:+ [$default]}: " value
    printf -v "$var" '%s' "${value:-$default}"
  else
    printf -v "$var" '%s' "$default"
  fi
}

ask GROVS_DOMAIN "Your domain (dashboard, API and links live under it)" example.com
ask GROVS_TEST_DOMAIN "Test-environment domain (Enter for the default)" "test.${GROVS_DOMAIN}"
ask GROVS_ADMIN_EMAIL "Admin email (first login, Let's Encrypt account)" "admin@${GROVS_DOMAIN}"

D="$GROVS_DOMAIN"; T="$GROVS_TEST_DOMAIN"
set_env DASHBOARD_HOST "dashboard.$D"
set_env API_HOST "api.$D"
set_env SDK_HOST "sdk.$D"
set_env MCP_HOST "mcp.$D"
set_env GO_HOST "go.$D"
set_env LINKS_PROD_HOST "links.$D"
set_env LINKS_TEST_HOST "links.$T"
set_env PREVIEW_HOST "preview.$D"
set_env ACME_EMAIL "$GROVS_ADMIN_EMAIL"
set_env SERVER_HOST "$D"
set_env REACT_HOST "dashboard.$D"
set_env DOMAIN_LIVE "$D"
set_env DOMAIN_TEST "$T"
set_env PREVIEW_BASE_URL "https://preview.$D"
set_env MCP_CONSENT_URL "https://dashboard.$D/mcp/authorize"
set_env S3_ASSET_PREFIX "https://api.$D"
set_env SMTP_DOMAIN "$D"
set_env MAILER_FROM "Grovs <noreply@$D>"

set_env POSTGRES_PASSWORD "$(rnd 16)"
set_env CLICKHOUSE_PASSWORD "$(rnd 16)"
set_env SECRET_KEY_BASE "$(rnd 64)"
set_env ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY "$(rnd 16)"
set_env ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY "$(rnd 16)"
set_env ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT "$(rnd 16)"
set_env ADMIN_API_KEY "$(rnd 24)"
set_env DIAGNOSTICS_API_KEY "$(rnd 24)"
set_env SENT_QUOTAS_WEBHOOK_KEY "$(rnd 24)"
set_env OAUTH_CLIENT_UID "$(rnd 24)"
set_env OAUTH_CLIENT_SECRET "$(rnd 32)"
ADMIN_PW=$(rnd 12)
set_env BOOTSTRAP_ADMIN_EMAIL "$GROVS_ADMIN_EMAIL"
set_env BOOTSTRAP_ADMIN_PASSWORD "$ADMIN_PW"

echo
echo "Wrote .env for $D (test domain $T)."
echo "  Dashboard: https://dashboard.$D"
echo "  Login:     $GROVS_ADMIN_EMAIL / $ADMIN_PW"
echo "Set SMTP_* in .env if you want password-reset and invite emails."
