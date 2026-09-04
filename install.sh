#!/usr/bin/env bash
# One-command install: curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/main/install.sh | bash
set -euo pipefail

VERSION="${GROVS_VERSION:-2.3.0}"
DIR="${GROVS_DIR:-grovs}"
# Stack files track main; images are pinned by VERSION.
BASE="${GROVS_STACK_URL:-https://raw.githubusercontent.com/grovs-io/self-host/main}"

for cmd in docker curl openssl; do
  command -v "$cmd" >/dev/null || { echo "install.sh: $cmd is required" >&2; exit 1; }
done
docker compose version >/dev/null 2>&1 || { echo "install.sh: Docker Compose v2 is required" >&2; exit 1; }

mkdir -p "$DIR/scripts" && cd "$DIR"
for f in docker-compose.yml docker-compose.local.yml Caddyfile .env.example scripts/setup.sh; do
  curl -fsSL "$BASE/$f" -o "$f"
done
chmod +x scripts/setup.sh

if [ ! -f .env ]; then
  # Piped into bash, stdin is the script itself: prompt on the terminal when there is one.
  if [ -t 0 ]; then ./scripts/setup.sh
  elif ( : </dev/tty ) 2>/dev/null; then ./scripts/setup.sh </dev/tty
  else ./scripts/setup.sh
  fi
fi
awk -v v="$VERSION" 'BEGIN{FS="="} $1=="GROVS_VERSION"{print "GROVS_VERSION="v; next} {print}' .env > .env.tmp && mv .env.tmp .env

if grep -q '^GROVS_LOCAL=true' .env; then
  COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.local.yml)
  url="http://dashboard.lvh.me:$(grep -E '^GROVS_DASHBOARD_PORT=' .env | cut -d= -f2-)"
else
  COMPOSE=(docker compose --profile standalone)
  url="https://$(grep -E '^DASHBOARD_HOST=' .env | cut -d= -f2-)"
fi
"${COMPOSE[@]}" pull
"${COMPOSE[@]}" up -d

echo
echo "Grovs $VERSION is starting."
grep -q '^GROVS_LOCAL=true' .env || echo "  Certificates are issued on the first request to each host."
echo "  Dashboard: $url"
echo "  Login:     $(grep -E '^BOOTSTRAP_ADMIN_EMAIL=' .env | cut -d= -f2-) / $(grep -E '^BOOTSTRAP_ADMIN_PASSWORD=' .env | cut -d= -f2-)"
echo "  Files:     $(pwd)   (logs: docker compose logs -f web)"
