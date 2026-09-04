#!/usr/bin/env bash
# One-command Grovs install:
#   curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/main/install.sh | bash
# Downloads the stack files into ./grovs (GROVS_DIR), asks for your domains, generates
# secrets, pulls the published images and starts everything with automatic TLS.
# Point DNS at this host first (see README: DNS). Re-run to upgrade: it keeps .env.
set -euo pipefail

VERSION="${GROVS_VERSION:-2.3.0}"
DIR="${GROVS_DIR:-grovs}"
BASE="https://raw.githubusercontent.com/grovs-io/self-host/${VERSION}"

for cmd in docker curl openssl; do
  command -v "$cmd" >/dev/null || { echo "install.sh: $cmd is required" >&2; exit 1; }
done
docker compose version >/dev/null 2>&1 || { echo "install.sh: Docker Compose v2 is required" >&2; exit 1; }

mkdir -p "$DIR/scripts" && cd "$DIR"
for f in docker-compose.yml Caddyfile .env.example scripts/setup.sh; do
  curl -fsSL "$BASE/$f" -o "$f"
done
chmod +x scripts/setup.sh

if [ ! -f .env ]; then
  # The script is piped into bash, so prompts must read from the terminal.
  ./scripts/setup.sh </dev/tty
fi
awk -v v="$VERSION" 'BEGIN{FS="="} $1=="GROVS_VERSION"{print "GROVS_VERSION="v; next} {print}' .env > .env.tmp && mv .env.tmp .env

docker compose --profile standalone pull
docker compose --profile standalone up -d

host=$(grep -E '^DASHBOARD_HOST=' .env | cut -d= -f2-)
echo
echo "Grovs $VERSION is starting. Certificates are issued on first request."
echo "  Dashboard: https://$host"
echo "  Login:     $(grep -E '^BOOTSTRAP_ADMIN_EMAIL=' .env | cut -d= -f2-) / $(grep -E '^BOOTSTRAP_ADMIN_PASSWORD=' .env | cut -d= -f2-)"
echo "  Files:     $(pwd)   (logs: docker compose logs -f web)"
