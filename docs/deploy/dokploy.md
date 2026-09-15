# Deploy with Dokploy

Use an existing Dokploy installation with Traefik. Grovs runs as a **Docker
Compose** service, not a Docker Swarm stack. Its template supplies routing for
the dashboard, API and dynamic project-link hosts.

## 1. Prepare your proxy and DNS

Point the [Grovs DNS records](server.md#2-configure-dns) at the server. Configure
a Traefik certificate resolver using **DNS-01 validation** for the app, production
links and test links domains. DNS-provider credentials belong to the proxy.

Dokploy's ordinary per-host HTTP certificate challenge cannot issue wildcard
certificates. Follow its [Traefik guide](https://docs.dokploy.com/docs/core/domains)
and [certificate documentation](https://docs.dokploy.com/docs/core/certificates).
The resolver name is supplied to Grovs as `GROVS_CERT_RESOLVER`.

## 2. Generate your environment

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
GROVS_DOMAIN=example.com GROVS_ADMIN_EMAIL=admin@example.com \
  ./scripts/prepare-platform.sh dokploy "$HOME/grovs-dokploy"
```

Setup writes `$HOME/grovs-dokploy/.env` and prints the first admin login. Preserve
this file. Set `GROVS_VERSION` to choose another published release, or
`GROVS_LINKS_DOMAIN` for a separate short-link domain.

## 3. Create the Compose service

In your project, create a **Compose** service:

| Setting | Value |
|---|---|
| Source | Git repository: `https://github.com/grovs-io/self-host` |
| Compose path | `docker-compose.platform.yml` |
| Deployment type | Docker Compose |
| Automatic deployments | Disabled; upgrade deliberately |

Paste the generated `.env` into Environment. Keep the template's explicit
network configuration; disable automatic network isolation/rewriting for this
manual routing setup. Leave Domains empty so Dokploy does not generate competing
routers. The template follows Dokploy's
[manual Compose routing model](https://docs.dokploy.com/docs/core/docker-compose/domains).

Confirm the proxy settings match your installation:

```dotenv
GROVS_PROXY_NETWORK=dokploy-network
GROVS_HTTP_ENTRYPOINT=web
GROVS_HTTPS_ENTRYPOINT=websecure
GROVS_CERT_RESOLVER=letsencrypt
```

The resolver must use DNS-01. Keep `GROVS_ROUTER_PREFIX` unique per deployment.
Only `web` and `dashboard` join the proxy network; databases remain on the
stack's private network.

## 4. Deploy and check

Preview the Compose definition, then Deploy. The migration container should
finish successfully before the API starts. Open `https://dashboard.example.com`
with the generated admin login, check `https://api.example.com/up`, and create
and open a project link to verify wildcard routing and TLS.

Customer-owned custom domains require additional proxy routes and certificates.
For updates, select matching image versions, back up data, and rerun migrations
before recreating application services. See [upgrades](../../README.md#upgrades)
and [troubleshooting](troubleshooting.md).
