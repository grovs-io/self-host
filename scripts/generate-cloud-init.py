#!/usr/bin/env python3
"""Print first-boot user data for a fresh Ubuntu 24.04 cloud server. Reads no secrets."""
import argparse
import json
from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[1]


def cloud_config(domain, email, version, stack_ref):
    values = {"GROVS_DOMAIN": domain, "GROVS_ADMIN_EMAIL": email,
              "GROVS_VERSION": version, "GROVS_STACK_REF": stack_ref}
    exports = "\n".join("export " + key + "=" + shlex.quote(value) for key, value in values.items())
    script = "#!/usr/bin/env bash\nset -euo pipefail\n" + exports + "\n" + (ROOT / "deploy/vm/bootstrap.sh").read_text()
    return {"write_files": [{"path": "/root/grovs-bootstrap.sh", "owner": "root:root",
                             "permissions": "0700", "content": script}],
            "runcmd": [["bash", "/root/grovs-bootstrap.sh"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True, help="App base domain without a scheme or path")
    parser.add_argument("--email", required=True, help="First administrator's email")
    parser.add_argument("--version", default="2.3.1", help="Published image release")
    parser.add_argument("--stack-ref", default="d9f291fb7a943adc8b712696342180ea63438cfd", help="Reviewed self-host Git commit")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z0-9-]+", args.domain) or args.domain.endswith("lvh.me"):
        parser.error("--domain must be a public hostname without a scheme, port or path")
    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", args.email):
        parser.error("--email must be an email address")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", args.version):
        parser.error("--version must be a published release number")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", args.stack_ref):
        parser.error("--stack-ref must be a Git commit, tag or branch")
    # JSON is valid YAML: avoids quoting surprises in embedded shell scripts.
    print("#cloud-config\n" + json.dumps(cloud_config(args.domain, args.email, args.version, args.stack_ref), indent=2))


if __name__ == "__main__":
    main()
