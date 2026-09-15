#!/usr/bin/env bash
# Generate a private environment file for the shared Coolify/Dokploy template.
set -euo pipefail
umask 077
STACK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $# -ne 2 || ( "$1" != coolify && "$1" != dokploy ) ]]; then
  echo "Usage: GROVS_DOMAIN=example.com GROVS_ADMIN_EMAIL=admin@example.com $0 coolify|dokploy OUTPUT_DIRECTORY" >&2
  exit 1
fi
: "${GROVS_DOMAIN:?Set your public app domain, e.g. example.com}"
[[ "$GROVS_DOMAIN" != local && "$GROVS_DOMAIN" != lvh.me ]] || {
  echo "Use scripts/setup.sh for a local trial." >&2; exit 1;
}
for domain in "$GROVS_DOMAIN" "${GROVS_LINKS_DOMAIN:-$GROVS_DOMAIN}" "${GROVS_TEST_DOMAIN:-test.${GROVS_LINKS_DOMAIN:-$GROVS_DOMAIN}}"; do
  [[ "$domain" =~ ^[a-z0-9][a-z0-9.-]*\.[a-z0-9-]+$ ]] || {
    echo "Domains must be lowercase hostnames without a scheme, port or path." >&2; exit 1;
  }
done
mkdir -p "$2"
OUTPUT="$(cd "$2" && pwd)"
if [[ -e "$OUTPUT/.env" ]]; then
  echo "$OUTPUT/.env already exists; keeping its secrets and platform settings."
  exit 0
fi
GROVS_CONFIG_DIR="$OUTPUT" "$STACK_DIR/scripts/setup.sh"
get_env() { sed -n "s/^$1=//p" "$OUTPUT/.env"; }
LINKS_DOMAIN="$(get_env DOMAIN_LIVE)"
TEST_DOMAIN="$(get_env DOMAIN_TEST)"
if [[ "$1" == coolify ]]; then
  HTTP_ENTRYPOINT=http; HTTPS_ENTRYPOINT=https; PROXY_NETWORK=coolify
else
  HTTP_ENTRYPOINT=web; HTTPS_ENTRYPOINT=websecure; PROXY_NETWORK=dokploy-network
fi
# The panel chooses the Compose project name. A unique router prefix prevents
# collisions if multiple Grovs installations share the same Traefik proxy.
sed '/^COMPOSE_PROJECT_NAME=/d' "$OUTPUT/.env" > "$OUTPUT/.env.tmp"
mv "$OUTPUT/.env.tmp" "$OUTPUT/.env"
cat >> "$OUTPUT/.env" <<ENV

# Platform proxy: resolver must already use DNS-01 for wildcard certificates.
GROVS_ROUTER_PREFIX=grovs-$(openssl rand -hex 4)
GROVS_PROXY_NETWORK=$PROXY_NETWORK
GROVS_HTTP_ENTRYPOINT=$HTTP_ENTRYPOINT
GROVS_HTTPS_ENTRYPOINT=$HTTPS_ENTRYPOINT
GROVS_CERT_RESOLVER=letsencrypt
GROVS_LINKS_DOMAIN_PATTERN=${LINKS_DOMAIN//./[.]}
GROVS_TEST_DOMAIN_PATTERN=${TEST_DOMAIN//./[.]}
ENV
echo "Import $OUTPUT/.env into the platform's environment editor."
echo "Use docker-compose.platform.yml and the guide at docs/deploy/$1.md."
