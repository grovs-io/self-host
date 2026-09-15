#!/usr/bin/env bash
# <UDF name="grovs_domain" label="App domain, without https://" example="grovs.example.com">
# <UDF name="grovs_admin_email" label="First administrator email" example="admin@example.com">
# <UDF name="sudo_user_name" label="SSH administrator username" default="grovsadmin">
# <UDF name="pubkey" label="SSH public key for the administrator">
# <UDF name="ssh_source_cidr" label="Your public IPv4 followed by /32" example="203.0.113.10/32">
set -euo pipefail
umask 077
: "${GROVS_DOMAIN:?}" "${GROVS_ADMIN_EMAIL:?}" "${SUDO_USER_NAME:?}" "${PUBKEY:?}" "${SSH_SOURCE_CIDR:?}"
WORK_DIR=$(mktemp -d /opt/grovs-marketplace.XXXXXX)
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT
trap 'echo "Grovs marketplace setup failed at line $LINENO" >&2' ERR
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y git python3-venv
# Resolve installer code from a fixed package revision; override only after review.
git clone --quiet https://github.com/grovs-io/self-host.git "$WORK_DIR/source"
git -C "$WORK_DIR/source" checkout --quiet --detach "${GROVS_CATALOG_REF:-01d739ebc6b5be4d7d61a097c292b242035e52f9}"
cd "$WORK_DIR/source/deploy/catalogs/akamai/apps/linode-marketplace-grovs"
python3 -m venv "$WORK_DIR/venv"
"$WORK_DIR/venv/bin/pip" install --quiet -r requirements.txt
"$WORK_DIR/venv/bin/ansible-playbook" provision.yml
"$WORK_DIR/venv/bin/ansible-playbook" site.yml
echo "Grovs setup completed. Configure DNS and read the .credentials file in your SSH administrator's home."
