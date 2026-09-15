#!/usr/bin/env bash
# Packer build VM only. Stops before initialization: no credentials or data baked in.
set -euo pipefail
umask 077
[[ $(id -u) == 0 ]] || exit 1
[[ "${GROVS_IMAGE_BUILD:-}" == 1 ]] || { echo 'Set GROVS_IMAGE_BUILD=1 on a disposable image builder.' >&2; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || exit 1
[[ ! -e /opt/grovs ]] || { echo '/opt/grovs already exists; refuse to bake a used installation.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y ca-certificates curl git openssl docker.io docker-compose-v2 ufw
systemctl enable --now docker
install -d -m 0755 /usr/local/lib/grovs
install -m 0755 /opt/grovs-catalog-input/grovs-setup.sh /usr/local/bin/grovs-setup
install -m 0644 /opt/grovs-catalog-input/bootstrap.sh /usr/local/lib/grovs/bootstrap.sh
git clone --quiet https://github.com/grovs-io/self-host.git /opt/grovs
git -C /opt/grovs checkout --quiet --detach d9f291fb7a943adc8b712696342180ea63438cfd
chmod 700 /opt/grovs
# Pull public images only; never run setup.sh or start a container on the build VM.
for image in ghcr.io/grovs-io/backend:2.3.1 ghcr.io/grovs-io/dashboard:2.3.1 postgres:16-alpine redis:7-alpine clickhouse/clickhouse-server:25.3 caddy:2; do
  docker pull "$image"
done
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
cat > /etc/update-motd.d/99-grovs <<'MOTD'
#!/bin/sh
printf '\nGrovs Community: https://www.grovs.io\n'
printf 'First setup: sudo grovs-setup grovs.example.com admin@example.com\n'
printf 'Guide: https://github.com/grovs-io/self-host/tree/main/deploy/catalogs\n\n'
MOTD
chmod 755 /etc/update-motd.d/99-grovs
[[ ! -e /opt/grovs/.env ]]
[[ -z "$(docker ps -aq)" && -z "$(docker volume ls -q)" ]] || { echo 'Image builder contains containers or volumes; refuse snapshot.' >&2; exit 1; }
