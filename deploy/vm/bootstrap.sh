#!/usr/bin/env bash
# Run as root on a fresh Ubuntu 24.04 VM. Never prints generated credentials.
set -euo pipefail
umask 077
: "${GROVS_DOMAIN:?Set the app domain}"
: "${GROVS_ADMIN_EMAIL:?Set the admin email}"
: "${GROVS_VERSION:?Set a published release version}"
STACK_REF="${GROVS_STACK_REF:-main}"
[[ "$GROVS_DOMAIN" != local && "$GROVS_DOMAIN" != lvh.me ]] || {
  echo "Cloud deployments require a public domain." >&2; exit 1;
}
[[ $(id -u) == 0 ]] || { echo "Run bootstrap.sh as root." >&2; exit 1; }
# Provided by Ubuntu on the target VM; absent on macOS validation hosts.
# shellcheck source=/dev/null
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || {
  echo "This bootstrap supports Ubuntu 24.04." >&2; exit 1;
}

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y ca-certificates curl git openssl docker.io docker-compose-v2
systemctl enable --now docker

# Do not replace an existing checkout or regenerate an existing installation's secrets.
if [[ ! -d /opt/grovs ]]; then
  CHECKOUT="$(mktemp -d /opt/grovs-install.XXXXXX)"
  trap 'rm -rf "$CHECKOUT"' EXIT
  git clone --quiet https://github.com/grovs-io/self-host.git "$CHECKOUT"
  git -C "$CHECKOUT" checkout --quiet --detach "$STACK_REF"
  mv "$CHECKOUT" /opt/grovs
  trap - EXIT
fi
cd /opt/grovs
chmod 700 /opt/grovs
GROVS_CONFIG_DIR=/opt/grovs ./scripts/setup.sh > /opt/grovs/setup.log 2>&1
chmod 600 .env setup.log

cat > /etc/systemd/system/grovs.service <<'UNIT'
[Unit]
Description=Grovs Community Docker Compose stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/grovs
ExecStart=/usr/bin/docker compose --profile standalone up -d
ExecStop=/usr/bin/docker compose --profile standalone stop
TimeoutStartSec=1200
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
UNIT

docker compose --profile standalone pull
systemctl daemon-reload
systemctl enable --now grovs
echo "Grovs containers started. Configure DNS, then open https://dashboard.$GROVS_DOMAIN."
echo "Administrator credentials are in /opt/grovs/.env (root access required)."
