#!/usr/bin/env bash
# Runs on the customer's new VM, never while building a marketplace image.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
if [[ $# != 2 ]]; then echo 'Usage: sudo grovs-setup grovs.example.com admin@example.com' >&2; exit 1; fi
[[ "$1" =~ ^[a-z0-9][a-z0-9.-]*\.[a-z0-9-]+$ && "$1" != *lvh.me ]] || { echo 'Enter a public domain without a scheme or path.' >&2; exit 1; }
[[ "$2" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$ ]] || { echo 'Enter a valid administrator email.' >&2; exit 1; }
export GROVS_DOMAIN="$1" GROVS_ADMIN_EMAIL="$2"
export GROVS_VERSION=2.3.1
export GROVS_STACK_REF=d9f291fb7a943adc8b712696342180ea63438cfd
exec bash /usr/local/lib/grovs/bootstrap.sh < /dev/null
