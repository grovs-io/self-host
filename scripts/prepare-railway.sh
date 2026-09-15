#!/usr/bin/env bash
# Create private inputs for Railway IaC; never applies cloud changes.
set -euo pipefail
umask 077
[[ $# == 1 ]] || { echo "Usage: GROVS_DOMAIN=example.com $0 OUTPUT_DIRECTORY" >&2; exit 1; }
: "${GROVS_DOMAIN:?Set your public app domain}"
[[ "$GROVS_DOMAIN" != local && "$GROVS_DOMAIN" != lvh.me ]] || {
  echo "Railway needs a public domain." >&2; exit 1;
}
STACK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GROVS_CONFIG_DIR="$1" "$STACK_DIR/scripts/setup.sh"
if ! grep -q '^REDIS_PASSWORD=' "$1/.env"; then
  printf '\nREDIS_PASSWORD=%s\n' "$(openssl rand -hex 16)" >> "$1/.env"
fi
echo "Set AWS_S3_KEY_ID, AWS_S3_ACCESS_KEY, AWS_S3_REGION and AWS_S3_BUCKET in $1/.env."
echo "Then export GROVS_CONFIG_FILE with that file's absolute path. See docs/deploy/railway.md."
