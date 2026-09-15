#!/usr/bin/env bash
set -euo pipefail
[[ "${GROVS_IMAGE_BUILD:-}" == 1 && ! -e /opt/grovs/.env ]] || exit 1
[[ -z "$(docker ps -aq)" && -z "$(docker volume ls -q)" ]] || exit 1
REF=95768fc9438ac0024be291d328beca5844181c88
curl -fsSL "https://raw.githubusercontent.com/vultr/vultr-marketplace/$REF/helper-scripts/vultr-helper.sh" -o /root/grovs-vultr-helper.sh
# shellcheck source=/dev/null
source /root/grovs-vultr-helper.sh
install -d -m 0755 /var/lib/cloud/scripts/per-instance
install -m 0700 /opt/grovs-catalog-input/setup-per-instance.sh /var/lib/cloud/scripts/per-instance/grovs.sh
rm -rf /opt/grovs-catalog-input
clean_system
cloud-init clean --logs --machine-id
