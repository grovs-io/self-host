# Easypanel

Run Grovs on your Easypanel server using the native service template. It creates
the backend, dashboard, two workers and three databases with persistent volumes.

**Preview:** the template passes local checks; live Easypanel validation and an
official catalog listing are pending. Use manual import as described below.

[Get the Easypanel template](https://github.com/grovs-io/self-host/tree/main/deploy/catalogs/easypanel/grovs)

## 1. Prepare your server and storage

Use an existing Easypanel server with **4 vCPU / 8 GB RAM / 80 GB SSD**, domains
you control and a **private S3-compatible bucket** for uploads. Keep the bucket
credentials available for the template form. If you need to install the panel,
follow [Easypanel's setup guide](https://easypanel.io/docs).

Choose three domains, without a scheme or path:

| Setting | Example |
|---|---|
| App base domain | `grovs.example.com` |
| Production links domain | `links.example.com` |
| Test links domain | `test.links.example.com` |

## 2. Generate your template

Until Grovs is included in Easypanel's catalog, generate its configuration using
the [upstream template playground](https://github.com/easypanel-io/templates)
on your computer. This step needs **Node.js 22**, npm and Git. Grovs itself runs
from published images.

In a fresh directory:

```bash
git clone https://github.com/grovs-io/self-host.git grovs-self-host
git clone https://github.com/easypanel-io/templates.git grovs-easypanel
cp -R grovs-self-host/deploy/catalogs/easypanel/grovs grovs-easypanel/templates/grovs
cd grovs-easypanel
npm ci
npm run build-templates
npm run dev:next -- --port 3010
```

Open **http://localhost:3010/?slug=grovs**. Enter your domains, administrator
email and bucket details. Leave the storage endpoint empty for AWS S3; for
another provider, enter its S3-compatible HTTPS endpoint.

Select **Generate**, then **Copy**. The resulting JSON includes generated
passwords, encryption keys and the credentials you entered. Keep it private and
save a secure copy. Generate it once per installation: generating again creates
new secrets. Stop the local playground with Ctrl+C when finished.

## 3. Import into Easypanel

In your Easypanel project, create a template **from JSON**, paste the generated
configuration and create its services. Keep the default single replica per
service and zero-downtime replacement disabled.

Web waits for PostgreSQL and ClickHouse, runs migrations and initial setup, then
starts the API. The workers wait for the API's health endpoint. Database services
have persistent volumes and no public port mappings.

## 4. Configure domains and HTTPS

Point your [DNS records](server.md#2-configure-dns) at the Easypanel server.
The template attaches these fixed hosts on container port **3000**:

| Service | Hosts |
|---|---|
| Dashboard | `dashboard.<app domain>` |
| Web | `api`, `sdk`, `mcp`, `go` and `preview` under the app domain |

Add these domains to **web**, also on port 3000:

- `links.<production links domain>` and `links.<test links domain>`.
- `*.<production links domain>` and `*.<test links domain>` for project links.

Configure wildcard routing and certificates through Easypanel's proxy settings.
Wildcard certificates need DNS validation or certificates you supply; a wildcard
DNS record alone does not enable HTTPS. Check both production and test project
hosts before using links in your apps.

## 5. Sign in and verify

Read `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from the web service's
environment. Open `https://dashboard.<app domain>` and sign in.

Check `https://api.<app domain>/up`, create a project and open a link. Verify its
analytics, an uploaded image, and production/test link HTTPS. Check web's logs
if migrations fail or the API does not become ready.

For updates, preserve all environment secrets, database volumes and bucket
contents. Back them up, stop workers, update both Grovs images to the same release,
let web complete migrations, then restart workers and dashboard. Keep `worker-1`
at one instance. Do not generate a replacement template over an existing install.

See [images and upgrades](../../README.md#upgrades),
[troubleshooting](troubleshooting.md) and the
[template package](../../deploy/catalogs/easypanel/README.md) for further details.
