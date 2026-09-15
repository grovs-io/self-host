# Deploy with Coolify

Use an existing Coolify server with a **Traefik** proxy. This guide uses the
repository's Compose template in **Raw Compose Deployment** mode, because Grovs
needs explicit routing for its dynamic project-link hostnames. It does not apply
to a Coolify server using the Caddy proxy.

## 1. Prepare your proxy and DNS

Point the [Grovs DNS records](server.md#2-configure-dns) at the deployment server.
Configure a Traefik certificate resolver with **DNS-01 validation** for your app,
production-links and test-links domains. Keep the DNS-provider token in the
proxy's configuration, not in the Grovs environment.

Follow Coolify's [DNS challenge](https://coolify.io/docs/core/networking/proxy/traefik/dns-challenge)
and [wildcard certificate](https://coolify.io/docs/core/networking/proxy/traefik/wildcard-certs)
instructions. A wildcard DNS record alone does not provide a wildcard certificate.

## 2. Generate your environment

On your workstation:

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
GROVS_DOMAIN=example.com GROVS_ADMIN_EMAIL=admin@example.com \
  ./scripts/prepare-platform.sh coolify "$HOME/grovs-coolify"
```

This writes `$HOME/grovs-coolify/.env`, generates credentials and prints your
admin login. It keeps existing files. Set `GROVS_VERSION` to select another
published release, or `GROVS_LINKS_DOMAIN` for a separate short-link domain.

## 3. Create the Compose application

In Coolify, select **New → Public Repository**, using
`https://github.com/grovs-io/self-host`:

| Setting | Value |
|---|---|
| Build Pack | Docker Compose |
| Base Directory | `/` |
| Docker Compose Location | `/docker-compose.platform.yml` |
| Raw Compose Deployment | Enabled |
| Automatic deployments | Disabled; upgrade deliberately |

Import the generated `.env` into the application's environment editor. Confirm:

- `GROVS_PROXY_NETWORK=coolify` matches the actual Traefik Docker network.
- `GROVS_HTTP_ENTRYPOINT=http` and `GROVS_HTTPS_ENTRYPOINT=https` match your proxy.
- `GROVS_CERT_RESOLVER=letsencrypt` names the resolver you configured for DNS-01.
- `GROVS_VERSION` names a release whose two public GHCR images exist.

Keep the generated `GROVS_ROUTER_PREFIX` unique per deployment. Leave the UI's
per-service Domains fields empty: this template supplies its own Traefik labels.
It does not start the standalone Caddy proxy or publish database ports.

## 4. Deploy and check

Select Deploy and watch the service logs. The migration container exits with
code 0, then the API, workers and dashboard start. If your Coolify version counts
one-shot services in aggregate health, exclude `migrate` from that health check.

Open `https://dashboard.example.com`. Then check `https://api.example.com/up`,
create a project and open its link. A working dashboard alone does not verify
the wildcard link route or certificate.

New custom customer-owned domains need corresponding proxy routes and
certificates; this template automatically covers only the configured Grovs domains.
Keep the platform environment and persistent volumes backed up. See
[troubleshooting](troubleshooting.md) and the upstream
[Compose guide](https://coolify.io/docs/applications/builds/docker-compose).
