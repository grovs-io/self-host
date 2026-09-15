# CapRover

Run Grovs on your CapRover server using its One Click App template. The template
creates the backend, dashboard, two workers, PostgreSQL, Redis and ClickHouse.

**Preview:** the template passes local checks; live CapRover validation and an
official catalog listing are pending. Use manual import as described below.

[Get the CapRover template](https://raw.githubusercontent.com/grovs-io/self-host/main/deploy/catalogs/caprover/grovs.yml)

## 1. Prepare your server and storage

Use an existing CapRover server with **4 vCPU / 8 GB RAM / 80 GB SSD**, domains
you control and a **private S3-compatible bucket**. If you need to install the
panel, follow [CapRover's setup guide](https://caprover.com/docs/get-started.html).

Have your bucket name, region, access key and secret available. Uploads use this
bucket so the API and workers can access the same files.

## 2. Import the template

Open the template using the button above and copy its full contents. In CapRover,
open **Apps → One-Click Apps/Databases**, select **\>\> TEMPLATE \<\<**, paste the
template and select **Next**. This follows CapRover's
[custom template import flow](https://github.com/caprover/one-click-apps#test-your-one-click-apps).

Choose an app name, such as `grovs`, and fill in:

| Setting | Example |
|---|---|
| App base domain | `grovs.example.com` |
| Production links domain | `links.example.com` |
| Test links domain | `test.links.example.com` |
| Administrator email | Your email for the first dashboard login |
| Object storage | Your private bucket and credentials |

Leave the storage endpoint empty for AWS S3. For another provider, enter its
S3-compatible HTTPS endpoint. Keep the generated database, OAuth, encryption and
admin secrets in place and save them securely.

Create the services. Web waits for the databases and completes migrations and
initial setup before starting the API. Workers then start when web is healthy.
Database services have persistent volumes and no public port mappings.

## 3. Attach domains and enable HTTPS

Point the [Grovs DNS records](server.md#2-configure-dns) at your CapRover server.
In each application's HTTP settings, use container port **3000** and attach:

| Application | Custom hosts |
|---|---|
| `grovs-dashboard` | `dashboard.<app domain>` |
| `grovs-web` | `api`, `sdk`, `mcp`, `go` and `preview` under the app domain |
| `grovs-web` | `links.<production links domain>`, `links.<test links domain>` |
| `grovs-web` | `*.<production links domain>`, `*.<test links domain>` |

Use your chosen app name in place of `grovs`. Enable HTTPS for fixed hosts, then
configure wildcard host routing and certificates covering both link domains.
Use DNS validation or supplied wildcard certificates; see
[CapRover's certificate configuration](https://caprover.com/docs/certbot-config).
Wildcard DNS alone does not supply HTTPS.

## 4. Sign in and verify

Read `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from the web app's
environment and sign in at `https://dashboard.<app domain>`.

Check `https://api.<app domain>/up`, create a project, open a link, inspect its
analytics and upload an image. Verify production and test project-link hosts
over HTTPS, including mobile association files. Check web's logs for startup or
migration failures.

Keep one instance of each service. In particular, stop the existing `worker-1`
before starting a replacement: it contains the scheduler. For upgrades, back up
databases, the bucket and environment secrets, then stop workers. Update both
Grovs images to the same release, wait for web to finish migrations and become
healthy, then restart workers and dashboard. Preserve all three database volumes;
do not reinstall the template over an existing deployment.

See [images and upgrades](../../README.md#upgrades),
[troubleshooting](troubleshooting.md) and the
[template package](../../deploy/catalogs/caprover/README.md) for further details.
