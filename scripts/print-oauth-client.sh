#!/usr/bin/env bash
# Print the dashboard OAuth client credentials (the deterministic React app).
# These are set in .env and seeded into the backend by backend-migrate.
set -euo pipefail
cd "$(dirname "$0")/.."

uid=$(grep -E '^OAUTH_CLIENT_UID=' .env | cut -d= -f2-)
secret=$(grep -E '^OAUTH_CLIENT_SECRET=' .env | cut -d= -f2-)

echo "OAUTH_CLIENT_UID    = ${uid}"
echo "OAUTH_CLIENT_SECRET = ${secret}"
echo
echo "The dashboard is built with NEXT_PUBLIC_CLIENT_ID=\${OAUTH_CLIENT_UID} and"
echo "CLIENT_SECRET=\${OAUTH_CLIENT_SECRET}, so no further wiring is needed."
