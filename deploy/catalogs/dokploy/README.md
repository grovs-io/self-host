# Dokploy template package

For a manual Compose import with wildcard routing, start with the
[Dokploy setup guide](../../../docs/deploy/dokploy.md). This directory holds the
native template candidate for the
[Dokploy template catalog](https://github.com/Dokploy/templates).

`grovs/` follows the catalog layout: `docker-compose.yml`, `template.toml`,
`meta.json` and `logo.svg`. It passes the upstream metadata, template and
Compose validators. Deployment in a Dokploy instance, wildcard HTTPS and
the upstream pull request are still pending.

## Prepare and validate the submission

Regenerate from the self-host root with
`python3 scripts/generate-panel-catalogs.py`. In a checkout of the upstream
repository, copy `grovs/` to `blueprints/grovs/`, then run:

```bash
node build-scripts/generate-meta.js --check
cd build-scripts && npm install
npx tsx validate-template.ts --dir ../blueprints/grovs
npx tsx validate-docker-compose.ts --file ../blueprints/grovs/docker-compose.yml
```

The validators check structure and naming. They do not start Grovs or verify
migrations, routing or HTTPS. Before an upstream PR, deploy the template on a
Dokploy instance and complete the [fresh-install scenarios](../README.md).

## Test it in your own Dokploy

`import.base64` is the same payload the catalog preview site produces. In
Dokploy, create a **Compose** service, open **Advanced**, scroll to
**Import**, paste the file's content and confirm. Dokploy fills in the Compose
file, generates the secrets, creates the domains and adds the environment.
Then deploy.

## What the first deployment looks like

The catalog cannot ask for input, so the template starts on a generated
placeholder host on `sslip.io` over HTTP. Dokploy creates the fixed hosts for
you: `dashboard`, `api`, `sdk`, `mcp`, `go`, `preview`, `links` and
`links.test`, all under the placeholder domain and pointing at container port
3000. Per-project link hosts such as `<project>.<placeholder>` are routed by
wildcard Traefik rules carried in the Compose file, so no manual domain entry
is needed. Grovs always prints project links with `https://`; on the
placeholder there is no certificate, so open them with `http://` instead.
Uploads use the `storage` volume; no object storage is required.

Sign in at the dashboard host with `BOOTSTRAP_ADMIN_EMAIL` and
`BOOTSTRAP_ADMIN_PASSWORD` from the service's **Environment** tab. Save the
generated environment securely; every secret is created once per installation
and shared by the services that need it.

## Move to your own domain

Every host is derived inside the Compose file from four environment values, so
switching domains does not require editing the Compose file:

| Variable | Set it to | Example |
|---|---|---|
| `SERVER_HOST` | App domain | `grovs.example.com` |
| `DOMAIN_LIVE` | Production links domain | `links.example.com` |
| `DOMAIN_TEST` | Test links domain | `test.links.example.com` |
| `SERVER_HOST_PROTOCOL` | `https://` once certificates are in place | `https://` |
| `GROVS_CERT_RESOLVER` | Name of a Traefik resolver that uses DNS-01 | `letsencrypt-dns` |

Then, in **Domains**, replace the placeholder hosts with the same names under
your domain, enable HTTPS, point the DNS records at the server and redeploy.
`dashboard.<app domain>` goes to `dashboard`; `api`, `sdk`, `mcp`, `go` and
`preview` under the app domain plus `links.<production links domain>` and
`links.<test links domain>` go to `web`.

Project links live on `*.<production links domain>` and
`*.<test links domain>`. The Compose file already routes both wildcards to
`web` on HTTP and HTTPS, so Dokploy's Domains tab does not need entries for
them. HTTPS for wildcard hosts requires a wildcard certificate, which Let's
Encrypt only issues through DNS-01. Configure a resolver with your DNS
provider's credentials in Dokploy's Traefik configuration, put its name in
`GROVS_CERT_RESOLVER`, point wildcard DNS records at the server and redeploy.
Until then Traefik serves its default certificate on those hosts. The
[Dokploy guide](../../../docs/deploy/dokploy.md) covers the resolver setup.
Verify a new project's production and test host over HTTPS, including the
mobile association files.

## Startup, operation and updates

`migrate` runs the PostgreSQL and ClickHouse migrations and seeds the first
admin and OAuth client; `web` starts only after it succeeds and the workers
and dashboard wait for the web health check. If the API does not become
ready, read the `migrate` logs first.

Keep one replica of every service. `worker-1` runs the scheduler and must never
be scaled. Databases stay on the stack's private network with persistent
volumes and no published ports. To upgrade, back up the databases, the storage
volume and the environment, then set both Grovs image tags to the same release
in the Compose file and redeploy; `migrate` runs again before `web` restarts.
Do not reimport the template over an existing installation, because it
regenerates the secrets.

Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
