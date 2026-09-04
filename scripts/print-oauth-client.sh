#!/usr/bin/env bash
# Print the dashboard OAuth client credentials (the deterministic React app in .env).
set -euo pipefail
cd "$(dirname "$0")/.."
echo "OAUTH_CLIENT_UID    = $(grep -E '^OAUTH_CLIENT_UID=' .env | cut -d= -f2-)"
echo "OAUTH_CLIENT_SECRET = $(grep -E '^OAUTH_CLIENT_SECRET=' .env | cut -d= -f2-)"
