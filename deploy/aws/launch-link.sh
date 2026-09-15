#!/usr/bin/env bash
# Generates a Launch Stack URL after the template has been uploaded to S3.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: $0 REGION HTTPS_S3_TEMPLATE_URL" >&2
  exit 1
fi
python3 - "$1" "$2" <<'PY'
import re
import sys
from urllib.parse import urlencode, urlparse
region, template = sys.argv[1:]
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d+", region):
    raise SystemExit("Invalid AWS region")
url = urlparse(template)
if url.scheme != "https" or not url.netloc.endswith(".amazonaws.com"):
    raise SystemExit("Supply the HTTPS URL of your template in Amazon S3")
query = urlencode({"templateURL": template, "stackName": "grovs-community"})
print(f"https://{region}.console.aws.amazon.com/cloudformation/home?region={region}#/stacks/create/review?{query}")
PY
