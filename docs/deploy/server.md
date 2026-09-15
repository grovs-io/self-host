# Run Grovs on a server

This runs the entire Community stack on one Linux server. You control the
databases and uploads, and the bundled Caddy proxy handles HTTPS.

## Before starting

- Docker Engine and Docker Compose v2 installed.
- Plan for at least 4 vCPU, 8 GB RAM and 80 GB SSD; allow more room as data grows.
- A public IPv4 address and a domain whose DNS you can change.
- Ports 80 and 443 available for Grovs. If Coolify or Dokploy already owns those
  ports, follow its [platform guide](README.md) instead.

The sizing above is a starting point, not a traffic guarantee. Workload, event
volume and retention determine the capacity you need.

## 1. Download and configure

```bash
git clone https://github.com/grovs-io/self-host.git grovs
cd grovs
GROVS_DOMAIN=example.com GROVS_ADMIN_EMAIL=admin@example.com ./scripts/setup.sh
```

Replace the example domain and email. Setup generates secrets and prints the
first administrator login. It preserves an existing `.env` on subsequent runs.
Keep this file private and backed up: it contains encryption keys needed to read
your stored configuration.

Use `GROVS_LINKS_DOMAIN=acme.link` if production short links should use a separate
domain. The default test links domain is `test.<links-domain>`; override it with
`GROVS_TEST_DOMAIN`. Use a bare domain, without `https://`, a port or a path.

Select a published release with `GROVS_VERSION` during setup, or edit that value
in `.env` before deploying. Both application images use the same version.

## 2. Configure DNS

With one domain (`example.com`), create these **A records**, all pointing to the
server's public IPv4:

| Name | Destination |
|---|---|
| `dashboard`, `api`, `sdk`, `mcp`, `go`, `preview` | Fixed application hosts |
| `links`, `links.test` | Reserved link hosts |
| `*` | Per-project production links |
| `*.test` | Per-project test links |

Only add AAAA records if this server also has working public IPv6. Start with
DNS-only records if your DNS provider offers a proxy. Separate app/links domains
are covered in the [full DNS reference](../../README.md#dns).

## 3. Start

```bash
docker compose --profile standalone pull
docker compose --profile standalone up -d
docker compose --profile standalone ps -a
docker compose --profile standalone logs --tail=100 migrate web
```

Wait for `migrate` to finish successfully and `web` to become healthy. Then open
**https://dashboard.example.com** and use the generated administrator login.
Check the API with `curl --fail https://api.example.com/up`.

Caddy obtains certificates for the fixed hosts and obtains project-link
certificates on demand. For reliable first-time mobile association requests,
configure wildcard certificates through your DNS provider before sending real
mobile traffic; see [TLS / Universal Links](../../README.md#dns).

## 4. Verify and operate

Create a project, create a link, open it, and check analytics. Configure the SDKs
using `https://sdk.example.com` and your project's API key.

- [Change settings](../../README.md#after-install-changing-settings)
- [Upgrade to a new release](../../README.md#upgrades)
- [Back up databases, uploads and secrets](../../README.md#backups)
- [Troubleshoot deployment](troubleshooting.md)

The scheduler in `worker-1` must have exactly one replica. The three database
services are private to the Compose network; do not publish their ports.
