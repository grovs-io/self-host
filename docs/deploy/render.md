# Deploy on Render

[Deploy on Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fgrovs-io%2Fself-host)

The repository's [render.yaml](../../render.yaml) Blueprint creates two public
services (API and dashboard), two workers, private ClickHouse with a persistent
disk, managed PostgreSQL and Key Value. All services use published images and
run in Frankfurt by default. **This is a paid deployment**, plus object storage.
Review the plans and disks in the Blueprint before confirming.

## 1. Prepare domains and object storage

Choose three hostnames, without a scheme or port:

| Input | Example |
|---|---|
| `SERVER_HOST` — app domain | `grovs.example.com` |
| `DOMAIN_LIVE` — production links | `links.example.com` |
| `DOMAIN_TEST` — test links | `test.links.example.com` |
| Dashboard `API_URL` | `https://api.grovs.example.com` |

Use dedicated subdomains if your main domain already hosts a website. Render's
wildcard setup requires the corresponding root domain to point to Render too.
[Render custom domains](https://render.com/docs/custom-domains)

Create an Amazon S3 bucket and credentials with access to that bucket. Supply
`AWS_S3_KEY_ID`, `AWS_S3_ACCESS_KEY`, `AWS_S3_REGION` and `AWS_S3_BUCKET` during
setup. Use bucket-scoped permissions for listing, reading, writing and deleting
Grovs objects. The backend and workers use the same bucket; keep it private.
This replaces the Compose upload volume, which cannot be shared between Render
services. [Persistent disks](https://render.com/docs/disks)

For S3-compatible storage, also configure `S3_ENDPOINT` and, if required,
`S3_FORCE_PATH_STYLE` on **all three backend services** before deploying them.

## 2. Create the Blueprint

Open the button above, or select **New → Blueprint** and connect the self-host
repository using `render.yaml`. Fill in the domain, bucket and admin email
prompts. Enter the dashboard `API_URL` from the table above.

Render generates secrets once. The workers and dashboard reference the web
service's values, including the shared OAuth credentials. The Blueprint connects
datastores through private service references. It does not publish database ports.
The API's pre-deploy command runs PostgreSQL migrations, seeds and ClickHouse
setup; worker startup waits for the API's health endpoint.

If ClickHouse or PostgreSQL is still starting and the first API pre-deploy step
fails, wait for both stores to be ready and deploy the API again. Inspect the
pre-deploy log before retrying a migration failure. Once healthy, retrieve
`BOOTSTRAP_ADMIN_PASSWORD` from **grovs-web → Environment**.

## 3. Add domains and HTTPS

In each web service's **Settings → Custom Domains**, add:

| Service | Domains, using the examples above |
|---|---|
| `grovs-dashboard` | `dashboard.grovs.example.com` |
| `grovs-web` | `api.grovs.example.com`, `sdk.grovs.example.com`, `mcp.grovs.example.com`, `go.grovs.example.com`, `preview.grovs.example.com` |
| `grovs-web` | `links.example.com`, `*.links.example.com`, `test.links.example.com`, `*.test.links.example.com` |

Copy the exact DNS records Render supplies, including wildcard certificate
verification records. Both wildcard levels need separate entries. Wait for
domain verification and certificate issuance before testing project links.
The service's generated `onrender.com` URL does not replace Grovs' hostname routes.

Check the API at `https://api.grovs.example.com/up`. Sign into the dashboard,
create a project, test production and test links, and confirm analytics arrive.
Upload an image and verify it remains accessible after redeploying the API.

## Operate and upgrade

Keep the scheduler's `grovs-worker-1` at one instance. Suspend both workers before
an upgrade so old and new scheduler processes do not overlap. Back up first,
update the two image tags together in the Blueprint, and sync it. Deploy the API
and verify migrations succeed, then resume the workers and deploy the dashboard.
Automatic image deployments are disabled.

Keep copies of the generated secrets and the bucket configuration. Back up
PostgreSQL, ClickHouse and uploads independently; a disk snapshot alone is not a
reliable database backup. [Render ClickHouse guidance](https://render.com/docs/deploy-clickhouse)

Deleting the Blueprint's resources can delete data. Export it first and review
which disks, database backups and external bucket remain. See
[troubleshooting](troubleshooting.md) and the
[Blueprint reference](https://render.com/docs/blueprint-spec).
