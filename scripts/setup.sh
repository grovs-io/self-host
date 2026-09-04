#!/usr/bin/env bash
# Create .env with strong secrets and your domains. Safe to re-run: keeps an existing .env.
# Non-interactive: GROVS_DOMAIN=acme.com [GROVS_LINKS_DOMAIN=acme.link] [GROVS_TEST_DOMAIN=...] GROVS_ADMIN_EMAIL=you@acme.com ./scripts/setup.sh
# Local trial: GROVS_DOMAIN=local ./scripts/setup.sh  (GROVS_WEB_PORT / GROVS_DASHBOARD_PORT optional)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists, keeping it (delete it to regenerate)."
  exit 0
fi
cp .env.example .env

rnd() { openssl rand -hex "$1"; }
set_env() {
  awk -v k="$1" -v v="$2" 'BEGIN{FS="="} $1==k{print k"="v; f=1; next} {print} END{if(!f) print k"="v}' .env > .env.tmp && mv .env.tmp .env
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

echo "Grovs needs a domain for real deep links. Press Enter to run a local trial on lvh.me instead."
ask GROVS_DOMAIN "App domain: dashboard, API and SDKs live under it (e.g. acme.com)" local
LOCAL=false
case "$GROVS_DOMAIN" in ""|local|lvh.me) LOCAL=true; GROVS_DOMAIN="lvh.me" ;; esac
if $LOCAL; then
  WEB_PORT="${GROVS_WEB_PORT:-80}"; DASH_PORT="${GROVS_DASHBOARD_PORT:-3002}"
  [ "$WEB_PORT" = "80" ] || GROVS_DOMAIN="lvh.me:$WEB_PORT"
  GROVS_LINKS_DOMAIN="$GROVS_DOMAIN"
  GROVS_TEST_DOMAIN="test.${GROVS_DOMAIN}"
  GROVS_ADMIN_EMAIL="${GROVS_ADMIN_EMAIL:-admin@example.com}"
else
  ask GROVS_LINKS_DOMAIN "Links domain: short links are <project>.<this> (Enter = app domain)" "$GROVS_DOMAIN"
  ask GROVS_TEST_DOMAIN "Test links domain (Enter for the default)" "test.${GROVS_LINKS_DOMAIN}"
  ask GROVS_ADMIN_EMAIL "Admin email: first login and Let's Encrypt account" "admin@${GROVS_DOMAIN}"
fi

A="$GROVS_DOMAIN"; L="$GROVS_LINKS_DOMAIN"; T="$GROVS_TEST_DOMAIN"
set_env DASHBOARD_HOST "dashboard.$A"
set_env API_HOST "api.$A"
set_env SDK_HOST "sdk.$A"
set_env MCP_HOST "mcp.$A"
set_env GO_HOST "go.$A"
set_env PREVIEW_HOST "preview.$A"
set_env LINKS_PROD_HOST "links.$L"
set_env LINKS_TEST_HOST "links.$T"
set_env ACME_EMAIL "$GROVS_ADMIN_EMAIL"
set_env SERVER_HOST "$A"
set_env REACT_HOST "dashboard.$A"
set_env DOMAIN_LIVE "$L"
set_env DOMAIN_TEST "$T"
set_env PREVIEW_BASE_URL "https://preview.$A"
set_env MCP_CONSENT_URL "https://dashboard.$A/mcp/authorize"
set_env S3_ASSET_PREFIX "https://api.$A"
set_env SMTP_DOMAIN "$A"
set_env MAILER_FROM "Grovs <noreply@$A>"
if $LOCAL; then
  set_env GROVS_LOCAL "true"
  set_env GROVS_WEB_PORT "$WEB_PORT"
  set_env GROVS_DASHBOARD_PORT "$DASH_PORT"
  set_env SERVER_HOST_PROTOCOL "http://"
  set_env REACT_HOST_PROTOCOL "http://"
  set_env REACT_HOST "dashboard.lvh.me:$DASH_PORT"
  set_env PREVIEW_BASE_URL "http://preview.$A"
  set_env MCP_CONSENT_URL "http://dashboard.lvh.me:$DASH_PORT/mcp/authorize"
  set_env S3_ASSET_PREFIX "http://api.$A"
fi

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
if $LOCAL; then
  echo "Wrote .env for a local trial on lvh.me."
  echo "  Dashboard: http://dashboard.lvh.me:$DASH_PORT"
else
  echo "Wrote .env: app on $A, links on $L, test links on $T."
  echo "  Dashboard: https://dashboard.$A"
fi
echo "  Login:     $GROVS_ADMIN_EMAIL / $ADMIN_PW"
$LOCAL || echo "Set SMTP_* in .env if you want password-reset and invite emails."
