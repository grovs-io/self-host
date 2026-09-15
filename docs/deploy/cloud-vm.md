# Ubuntu cloud server setup

Use a fresh **Ubuntu 24.04 x86_64** server with at least **4 vCPU, 8 GB RAM
and 80 GB SSD**, a public IPv4 address, an SSH key, and a domain you control.
The cloud provider bills your account for the server, storage and traffic.

## Install over SSH

On the new server, download the reviewed bootstrap script and inspect it:

```bash
curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/d9f291fb7a943adc8b712696342180ea63438cfd/deploy/vm/bootstrap.sh \
  -o /tmp/grovs-bootstrap.sh
less /tmp/grovs-bootstrap.sh
```

Run it with your domain and email. This installs packages and creates the
installation under `/opt/grovs`:

```bash
sudo env GROVS_DOMAIN=grovs.example.com \
  GROVS_ADMIN_EMAIL=admin@example.com \
  GROVS_VERSION=2.3.1 \
  GROVS_STACK_REF=d9f291fb7a943adc8b712696342180ea63438cfd \
  bash /tmp/grovs-bootstrap.sh < /dev/null
```

Use the same published image version for the backend and dashboard. The source
commit selects the Compose and setup files. Generated credentials stay in
`/opt/grovs/.env`; the bootstrap does not print them into cloud logs.

Allow inbound TCP 80/443 and restrict TCP 22 to your public IP in the provider's
firewall. Leave the database ports private. If a host firewall is already active,
allow web traffic there too. Allow outbound DNS, HTTPS and package downloads.

## DNS and first login

Point the [DNS records](../../README.md#dns) at the server's public IPv4.
For `grovs.example.com`, this includes `dashboard.grovs.example.com`,
`api.grovs.example.com`, the other fixed hosts, `*.grovs.example.com`, and
`*.test.grovs.example.com`. Keep these records DNS-only if using Cloudflare.
Caddy handles HTTPS; the DNS guide also covers certificates for mobile app links.

Connect with your SSH key and check provisioning:

```bash
sudo systemctl status grovs --no-pager
sudo journalctl -u grovs --no-pager -n 100
sudo cat /opt/grovs/.env
```

Read `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from `.env` locally;
keep that file private. Open `https://dashboard.grovs.example.com`, log in,
create a project and a link, then open the link and check analytics.

## Maintain the server

The stack and configuration live in `/opt/grovs`; databases and uploads use
Docker volumes on the server disk. `grovs.service` starts the existing stack
after reboot. Follow [upgrades](../../README.md#upgrades) and
[backups](../../README.md#backups) from that directory using root access.

If startup fails, fix the reported error and rerun the installation command
with the same environment variables. The bootstrap preserves an existing `.env`.
It starts the containers; check `sudo docker compose --project-directory /opt/grovs ps -a`
and the `migrate` service logs if the dashboard is not ready.

Before removing the server, back up the databases, uploads and `.env` outside
that server. Deleting a server or disk can destroy the stored data. Review the
provider's console for any retained disks, IPs and backups that continue billing.
