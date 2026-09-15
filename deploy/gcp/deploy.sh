#!/usr/bin/env bash
# Run from Cloud Shell or a workstation with gcloud. No credentials in metadata.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ "${1:-}" == --help ]]; then
  echo "Usage: $0 PROJECT_ID ZONE APP_DOMAIN ADMIN_EMAIL [RELEASE]"
  echo "Creates a dedicated network, static IP, firewall rules and Ubuntu VM."
  echo "Optional: GROVS_INSTANCE_NAME=grovs GROVS_MACHINE_TYPE=e2-standard-4 GROVS_STACK_REF=main"
  exit 0
fi
[[ $# -ge 4 && $# -le 5 ]] || { "$0" --help; exit 1; }
PROJECT="$1"; ZONE="$2"; APP_DOMAIN="$3"; ADMIN_EMAIL="$4"
VERSION="${5:-2.3.0}"; NAME="${GROVS_INSTANCE_NAME:-grovs}"
STACK_REF="${GROVS_STACK_REF:-main}"
[[ "$NAME" =~ ^[a-z][a-z0-9-]{0,40}$ && "$ZONE" =~ ^[a-z]+-[a-z0-9]+[0-9]-[a-z]$ ]] || {
  echo "Invalid instance name or zone." >&2; exit 1;
}
[[ "$APP_DOMAIN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ && "$APP_DOMAIN" == *.* ]] || {
  echo "APP_DOMAIN must be a hostname without a scheme or path." >&2; exit 1;
}
[[ "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$ ]] || {
  echo "Invalid admin email." >&2; exit 1;
}
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-][a-zA-Z0-9.-]+)?$ ]] || {
  echo "RELEASE must be a published version." >&2; exit 1;
}
[[ "$STACK_REF" =~ ^[a-zA-Z0-9._/-]+$ ]] || { echo "Invalid stack ref." >&2; exit 1; }
REGION="${ZONE%-*}"
command -v gcloud >/dev/null || { echo "Install gcloud or use Cloud Shell." >&2; exit 1; }
echo "Project: $PROJECT | Zone: $ZONE | VM: $NAME (${GROVS_MACHINE_TYPE:-e2-standard-4})"
echo "Creates billable resources: VM, 100 GB disk and public IPv4."
read -r -p "Create this deployment? [y/N] " answer
[[ "$answer" == y || "$answer" == Y ]] || exit 0

# Explicit --project on every command avoids changing the user's gcloud defaults.
gcloud --project="$PROJECT" services enable compute.googleapis.com
gcloud --project="$PROJECT" compute networks create "$NAME-network" --subnet-mode=custom
gcloud --project="$PROJECT" compute networks subnets create "$NAME-subnet" \
  --network="$NAME-network" --region="$REGION" --range=10.42.0.0/24
gcloud --project="$PROJECT" compute addresses create "$NAME-ip" --region="$REGION"
IP="$(gcloud --project="$PROJECT" compute addresses describe "$NAME-ip" --region="$REGION" --format='value(address)')"
gcloud --project="$PROJECT" compute firewall-rules create "$NAME-web" \
  --network="$NAME-network" --allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0 --target-tags="$NAME"
# SSH only through Identity-Aware Proxy; no public SSH rule.
gcloud --project="$PROJECT" compute firewall-rules create "$NAME-ssh" \
  --network="$NAME-network" --allow=tcp:22 --source-ranges=35.235.240.0/20 --target-tags="$NAME"

STARTUP="$(mktemp)"
trap 'rm -f "$STARTUP"' EXIT
{
  echo '#!/usr/bin/env bash'
  echo 'set -euo pipefail'
  printf 'export GROVS_DOMAIN=%q GROVS_ADMIN_EMAIL=%q GROVS_VERSION=%q GROVS_STACK_REF=%q\n' \
    "$APP_DOMAIN" "$ADMIN_EMAIL" "$VERSION" "$STACK_REF"
  cat "$SCRIPT_DIR/../vm/bootstrap.sh"
} > "$STARTUP"
gcloud --project="$PROJECT" compute instances create "$NAME" --zone="$ZONE" \
  --machine-type="${GROVS_MACHINE_TYPE:-e2-standard-4}" \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB --boot-disk-type=pd-balanced --no-boot-disk-auto-delete \
  --subnet="$NAME-subnet" --address="$IP" --tags="$NAME" \
  --no-service-account --no-scopes --metadata=enable-oslogin=TRUE \
  --metadata-from-file="startup-script=$STARTUP"
echo "Point the DNS records in docs/deploy/server.md at $IP."
echo "Dashboard: https://dashboard.$APP_DOMAIN (after startup and DNS)."
echo "Access: gcloud --project=$PROJECT compute ssh $NAME --zone=$ZONE --tunnel-through-iap"
echo "Then: sudo cat /opt/grovs/.env"
