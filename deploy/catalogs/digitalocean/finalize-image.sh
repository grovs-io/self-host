#!/usr/bin/env bash
set -euo pipefail
[[ "${GROVS_IMAGE_BUILD:-}" == 1 && ! -e /opt/grovs/.env ]] || exit 1
[[ -z "$(docker ps -aq)" && -z "$(docker volume ls -q)" ]] || exit 1
REF=b70878804ca27c01d5f5e882d26485defbaba210
curl -fsSL "https://raw.githubusercontent.com/digitalocean/marketplace-partners/$REF/scripts/90-cleanup.sh" -o /root/grovs-do-cleanup.sh
curl -fsSL "https://raw.githubusercontent.com/digitalocean/marketplace-partners/$REF/scripts/99-img-check.sh" -o /root/grovs-do-check.sh
bash /root/grovs-do-cleanup.sh
bash /root/grovs-do-check.sh
# Clear the builder's cloud-init state so host identity is regenerated on deployment.
cloud-init clean --logs --machine-id
rm -f /root/grovs-do-cleanup.sh /root/grovs-do-check.sh
rm -rf /opt/grovs-catalog-input
