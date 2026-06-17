#!/usr/bin/env bash
# Generate a .env with strong secrets. Run once, then edit the domains by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists — not overwriting (delete it to regenerate)."
  exit 0
fi
cp .env.example .env

rnd() { openssl rand -hex "$1"; }
set_env() {
  awk -v k="$1" -v v="$2" 'BEGIN{FS="="} $1==k{print k"="v; next} {print}' .env > .env.tmp && mv .env.tmp .env
}

PG_PW=$(rnd 16)
MINIO_PW=$(rnd 16)
ADMIN_PW=$(rnd 12)

set_env SECRET_KEY_BASE "$(rnd 64)"
set_env ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY "$(rnd 16)"
set_env ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY "$(rnd 16)"
set_env ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT "$(rnd 16)"
set_env ADMIN_API_KEY "$(rnd 24)"
set_env DIAGNOSTICS_API_KEY "$(rnd 24)"
set_env SENT_QUOTAS_WEBHOOK_KEY "$(rnd 24)"

set_env POSTGRES_PASSWORD "$PG_PW"
set_env DATABASE_URL "postgres://grovs:${PG_PW}@postgres:5432/grovs_production"

# The backend authenticates to MinIO with the AWS_S3_* creds, so they must equal
# the MinIO root credentials.
set_env MINIO_ROOT_USER "grovs"
set_env MINIO_ROOT_PASSWORD "$MINIO_PW"
set_env AWS_S3_KEY_ID "grovs"
set_env AWS_S3_ACCESS_KEY "$MINIO_PW"

# Deterministic OAuth. NEXT_PUBLIC_CLIENT_ID/CLIENT_SECRET must equal these exact
# values (env_file passes them literally to the dashboard container).
OAUTH_UID=$(rnd 24)
OAUTH_SECRET=$(rnd 32)
set_env OAUTH_CLIENT_UID "$OAUTH_UID"
set_env OAUTH_CLIENT_SECRET "$OAUTH_SECRET"
set_env NEXT_PUBLIC_CLIENT_ID "$OAUTH_UID"
set_env CLIENT_SECRET "$OAUTH_SECRET"

set_env BOOTSTRAP_ADMIN_PASSWORD "$ADMIN_PW"

echo
echo "Generated .env with fresh secrets."
echo "  Bootstrap admin password: ${ADMIN_PW}"
echo
echo "Now edit .env and set:"
echo "  - the *_HOST domains and ACME_EMAIL"
echo "  - BOOTSTRAP_ADMIN_EMAIL (and S3_ASSET_PREFIX / SERVER_HOST / REACT_HOST to your API + dashboard hosts)"
echo "  - SMTP_* only if you need password-reset / data-export email"
