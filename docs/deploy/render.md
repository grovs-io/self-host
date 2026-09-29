# Deploy on Render

[Deploy on Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fgrovs-io%2Fself-host)

The repository's [render.yaml](../../render.yaml) Blueprint creates two public
services (API and dashboard), two workers, private ClickHouse with a persistent
disk, managed PostgreSQL and Key Value. All services use published images and
run in Frankfurt by default. **This is a paid deployment**, plus object storage.
Review the plans and disks in the Blueprint before confirming.

This Blueprint was deployed end to end on Render: migrations, workers, custom
domains with wildcard HTTPS, sign-in, project links, uploads to Google Cloud
Storage and analytics.

## 1. Prepare domains and object storage

Choose three hostnames, without a scheme or port:

| Input | Example |
|---|---|
| `SERVER_HOST`: app domain | `grovs.example.com` |
| `DOMAIN_LIVE`: production links | `links.example.com` |
| `DOMAIN_TEST`: test links | `test.links.example.com` |
| Dashboard `API_URL` | `https://api.grovs.example.com` |

Use dedicated subdomains if your main domain already hosts a website. You need
to be able to add CNAME records for these names.
[Render custom domains](https://render.com/docs/custom-domains)

Uploads go to a private bucket that the API and both workers share, because a
Render disk cannot be shared between services.
[Persistent disks](https://render.com/docs/disks) Any S3-compatible storage
works:

- **Amazon S3:** create a bucket and an access key limited to it (list, read,
  write and delete). Enter the bucket's region as `AWS_S3_REGION`.
- **Google Cloud Storage:** create a bucket, a service account with **Storage
  Object Admin** on that bucket, and an HMAC key for it under **Cloud Storage →
  Settings → Interoperability**. Use `auto` as `AWS_S3_REGION` and set
  `S3_ENDPOINT=https://storage.googleapis.com` (see step 2). New Google Cloud
  organizations block service account keys by default; override both
  `iam.disableServiceAccountKeyCreation` and
  `iam.managed.disableServiceAccountKeyCreation` for the project, and restore
  them when you delete the key.
- **Other providers** (Cloudflare R2, DigitalOcean Spaces, MinIO): use their
  S3-compatible HTTPS endpoint as `S3_ENDPOINT` and, if required,
  `S3_FORCE_PATH_STYLE`.

## 2. Create the Blueprint

Open the button above, or select **New → Blueprint** and connect the self-host
repository using `render.yaml`. Fill in the domain, bucket and admin email
prompts. Enter the dashboard `API_URL` from the table above.

If you use `S3_ENDPOINT` or `S3_FORCE_PATH_STYLE`, add them to **grovs-web,
grovs-worker-1 and grovs-worker-2** under **Environment**, then redeploy those
three. The workers do not copy these values from the API.

Render generates secrets once. The workers and dashboard reference the web
service's values, including the shared OAuth credentials. The Blueprint connects
datastores through private service references. It does not publish database ports.
The API's pre-deploy command waits for ClickHouse, then runs PostgreSQL
migrations, seeds and ClickHouse setup; worker startup waits for the API's
health endpoint. Once healthy, retrieve `BOOTSTRAP_ADMIN_PASSWORD` from
**grovs-web → Environment** and sign in with `BOOTSTRAP_ADMIN_EMAIL`.

Render asks for the prompted values only when the Blueprint is first created.
If that attempt fails and a later **Manual sync** creates `grovs-web`, add
`SERVER_HOST`, `DOMAIN_LIVE`, `DOMAIN_TEST`, `BOOTSTRAP_ADMIN_EMAIL` and the
four `AWS_S3_*` values to grovs-web yourself, and check `API_URL` on the
dashboard, before syncing again. The workers cannot be created until web has
them.

## 3. Add domains and HTTPS

In each web service's **Settings → Custom Domains**, add:

| Service | Domains, using the examples above |
|---|---|
| `grovs-dashboard` | `dashboard.grovs.example.com` |
| `grovs-web` | `api.grovs.example.com`, `sdk.grovs.example.com`, `mcp.grovs.example.com`, `go.grovs.example.com`, `preview.grovs.example.com` |
| `grovs-web` | `links.example.com`, `*.links.example.com`, `test.links.example.com`, `*.test.links.example.com` |

Then add these CNAME records at your DNS provider, and select **Verify** for
each domain in Render:

| Name | Points to |
|---|---|
| `dashboard.grovs.example.com` | `grovs-dashboard.onrender.com` |
| The other nine names above | `grovs-web.onrender.com` |
| `_acme-challenge.links.example.com` | `grovs-web.verify.renderdns.com` |
| `_cf-custom-hostname.links.example.com` | `grovs-web.hostname.renderdns.com` |
| `_acme-challenge.test.links.example.com` | `grovs-web.verify.renderdns.com` |
| `_cf-custom-hostname.test.links.example.com` | `grovs-web.hostname.renderdns.com` |

Use your services' actual `onrender.com` names if they differ. The two extra
records per links domain let Render issue and renew the wildcard certificates.
Certificates usually appear a few minutes after verification. The service's
generated `onrender.com` URL does not replace Grovs' hostname routes.

Check the API at `https://api.grovs.example.com/up`. Sign into the dashboard,
create a project, test production and test links, and confirm analytics arrive.
Upload an image and verify it remains accessible after redeploying the API.

## Email

To send email over SMTP, set `MAILER_DELIVERY_METHOD=smtp`, `SMTP_USERNAME` and
`SMTP_PASSWORD` on **grovs-web and both workers**, since Render cannot share
empty values between services. Set `SMTP_ADDRESS` and the other `SMTP_*`
values on grovs-web; the workers copy them.

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
