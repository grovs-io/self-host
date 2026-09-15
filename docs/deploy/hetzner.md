# Grovs on Hetzner

[Open Hetzner Console](https://console.hetzner.com)

Use a fresh **Ubuntu 24.04 x86_64** server with at least **4 vCPU, 8 GB RAM
and 80 GB SSD**, a public IPv4 address, an SSH key, and a domain you control.
The cloud provider bills your account for the server, storage and traffic.

## Create startup data

On your workstation, generate startup data with your domain and administrator email:

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
python3 scripts/generate-cloud-init.py \
  --domain grovs.example.com \
  --email admin@example.com > /tmp/grovs-cloud-init.yaml
```

The file installs Docker and the full Compose stack on first boot. It pins the
stack source to a reviewed commit and defaults to image release `2.3.1`. Use
`--version X.Y.Z` to select another published release. Passwords are generated on
the server; the startup file contains no generated credentials.
## Create the Cloud server

1. Open your Hetzner project and create a server. Select an x86 server type,
   the plain **Ubuntu 24.04** image, and sufficient disk space.
2. Enable public IPv4, add your SSH public key, and paste the generated file
   into the **Cloud config** field before creating the server.
3. Attach a Hetzner Firewall allowing inbound TCP 80/443 from the internet and
   TCP 22 only from your public IP. Allow outbound traffic.
4. Create the server and connect as `root` to its public IPv4 address.

Choose the plain Ubuntu image: the startup script installs the Docker packages
it needs. See Hetzner's [cloud-config guide](https://community.hetzner.com/tutorials/basic-cloud-config).

## DNS and first login

Point the [DNS records](../../README.md#dns) at the server's public IPv4.
For `grovs.example.com`, this includes `dashboard.grovs.example.com`,
`api.grovs.example.com`, the other fixed hosts, `*.grovs.example.com`, and
`*.test.grovs.example.com`. Keep these records DNS-only if using Cloudflare.
Caddy handles HTTPS; the DNS guide also covers certificates for mobile app links.

Connect with your SSH key and check provisioning:

```bash
sudo cloud-init status --wait
sudo systemctl status grovs --no-pager
sudo tail -100 /var/log/cloud-init-output.log
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

If startup fails, inspect the log above and fix the reported error before
running `sudo bash /root/grovs-bootstrap.sh` again. A successful cloud-init run
starts the containers; check `sudo docker compose --project-directory /opt/grovs ps -a`
and the `migrate` service logs if the dashboard is not ready.

Before removing the server, back up the databases, uploads and `.env` outside
that server. Deleting a server or disk can destroy the stored data. Review the
provider's console for any retained disks, IPs and backups that continue billing.
