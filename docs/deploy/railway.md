# Deploy on Railway

Deploy Grovs Community from the Railway template. It creates the API, dashboard,
two workers and three private database services with persistent volumes.

**Railway compute, volumes, network usage and your object storage are billable.**
The template has been deployed end to end on Railway: migrations, workers,
custom domains with wildcard HTTPS, sign-in, project links, uploads and
analytics.

## Choose a plan

| Plan | Runs Grovs? | Custom domains per service |
|---|---|---|
| Trial | No: limited to 5 services per project, Grovs needs 7 | 1 |
| Hobby | Yes, with the compact domain layout below | 2 |
| Pro | Yes, with the full domain layout | 20 |

## Prepare object storage

Uploads go to a private S3-compatible bucket that the API and both workers
share, because Railway volumes cannot be shared between services. Use
bucket-scoped credentials that can list, read, write and delete objects.

- **Amazon S3:** enter the bucket's region and leave `S3_ENDPOINT` empty.
- **Any other S3-compatible provider:** set `S3_ENDPOINT` to its S3 API endpoint
  and use the region it documents (often `auto`). Set
  `S3_FORCE_PATH_STYLE=false` if the provider only accepts virtual-hosted URLs.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/grovs-community)

## Deploy from the template

1. Open **Deploy on Railway** and choose your workspace.
2. Fill in the eight required variables on `web`: `SERVER_HOST`, `DOMAIN_LIVE`,
   `DOMAIN_TEST`, `BOOTSTRAP_ADMIN_EMAIL`, `AWS_S3_KEY_ID`, `AWS_S3_ACCESS_KEY`,
   `AWS_S3_REGION` and `AWS_S3_BUCKET`, plus `S3_ENDPOINT` for a provider other
   than Amazon S3. The workers copy these values from `web`.
3. Review the services, storage and estimated usage, then deploy. Railway
   generates the database passwords, application secrets and admin password.
   Keep these values when redeploying or upgrading.
4. Add your custom domains in Networking, all targeting port **3000**. For
   `SERVER_HOST=grovs.example.com`, `DOMAIN_LIVE=links.example.com` and
   `DOMAIN_TEST=test.links.example.com`:

   | Layout | Service | Custom domains |
   |---|---|---|
   | Full (Pro) | `dashboard` | `dashboard.grovs.example.com` |
   | Full (Pro) | `web` | `api.grovs.example.com`, `sdk.grovs.example.com`, `mcp.grovs.example.com`, `go.grovs.example.com`, `preview.grovs.example.com`, `*.links.example.com`, `*.test.links.example.com` |
   | Compact (Hobby) | `dashboard` | `dashboard.grovs.example.com` |
   | Compact (Hobby) | `web` | `*.grovs.example.com`, `*.links.example.com` |

   In the compact layout, `*.grovs.example.com` covers the API, SDK, MCP, go and
   preview hosts, and Railway still sends `dashboard.` to the dashboard. Test
   links (`*.test.links.example.com`) are not served; add that domain after
   moving to Pro.

5. For every domain, add all the records Railway shows at your DNS provider:
   the CNAME for the domain, an `_acme-challenge` CNAME for each wildcard, and
   the `_railway-verify` TXT record. Certificates stay at "validating
   ownership" until the TXT record exists; after that they are usually issued
   within a few minutes.
6. Sign in at your dashboard domain using the admin email and generated
   `BOOTSTRAP_ADMIN_PASSWORD` from `web`'s variables. Check the API `/up`
   endpoint, create a project, test links, upload an image and confirm
   analytics.

The API initializes PostgreSQL and ClickHouse before starting. If a database is
still starting during the first attempt, wait until it is ready and redeploy
`web`. Workers wait for API health. Keep `worker-1` at exactly one instance.

## Alternative: deploy with the CLI

For a configuration managed in files, use the native Railway infrastructure
definition below. It also declares the custom domains automatically, using the
full layout, so it needs the Pro plan. Choose this flow instead of deploying a
second copy from the template.

## 1. Prepare your configuration

Install Node.js 22 or later, the [Railway CLI](https://docs.railway.com/cli), and
OpenSSL. Clone the self-host repository:

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
npm --prefix .railway ci
GROVS_DOMAIN=grovs.example.com GROVS_LINKS_DOMAIN=links.example.com \
  GROVS_ADMIN_EMAIL=admin@example.com \
  ./scripts/prepare-railway.sh "$HOME/grovs-railway"
export GROVS_CONFIG_FILE="$HOME/grovs-railway/.env"
```

The private file contains generated secrets and your first admin login. Keep it
outside Git and back it up. Subsequent runs preserve it. Select a published
release with `GROVS_VERSION` in this file.

Create a private S3-compatible bucket (see
[Prepare object storage](#prepare-object-storage)) and add these values to the
same file (uncomment their example lines):

```dotenv
AWS_S3_KEY_ID=your-access-key
AWS_S3_ACCESS_KEY=your-secret-key
AWS_S3_REGION=your-bucket-region
AWS_S3_BUCKET=your-bucket-name
```

For a provider other than Amazon S3, also add `S3_ENDPOINT` and, if needed,
`S3_FORCE_PATH_STYLE`. The API and workers share the bucket; they cannot share a
Railway volume. [Railway volumes](https://docs.railway.com/volumes)

## 2. Review and apply

Create a new empty Railway project and environment, then link this directory to
it. Keep all services and their volumes in one region.

```bash
railway login
railway link
railway config plan
railway config apply
```

Verify the linked project/environment and proposed resources. `apply` asks for
confirmation. The private configuration is the source for managed variables;
update that file when changing settings. Avoid `--show-values`, which can print
secrets. This uses Railway's current project-level IaC, not the deprecated
per-service `railway.json` format.
[Railway IaC](https://docs.railway.com/infrastructure-as-code)

The three volumes mount at PostgreSQL's `/var/lib/postgresql/data`, Redis's
`/data` and ClickHouse's `/var/lib/clickhouse`. Redis uses AOF and `noeviction`.
Database services have no public domains or TCP proxies. Keep application
services always running; do not enable serverless sleeping for workers.

The API pre-deploy command initializes PostgreSQL and ClickHouse. Workers wait
for API health before starting. If a datastore is still starting when the first
pre-deploy command runs, wait for it to be ready and redeploy the API. Inspect
logs to distinguish readiness failures from migration errors.

## 3. Finish DNS and sign in

Open each service's Networking settings. The definition requests the dashboard
host on `dashboard`, and API/SDK/MCP/go/preview plus production/test wildcard
domains on `web`, all targeting port 3000. Add the exact DNS records Railway
supplies, including the `_acme-challenge` CNAMEs and `_railway-verify` TXT
records.

For the example above, project links use `*.links.example.com` and
`*.test.links.example.com`. Both require their own domain and certificate setup.
Keep verification records unproxied if using Cloudflare DNS.
[Railway wildcard domains](https://docs.railway.com/networking/domains/working-with-domains)

Open `https://dashboard.grovs.example.com` and use the login printed by setup.
Check `https://api.grovs.example.com/up`, create a project, open both production
and test links, and confirm analytics. Upload an image and verify it survives
an API redeployment.

## Updates and backups

Stop both workers before upgrading; `worker-1` must have exactly one running
scheduler, including during rollouts. Back up databases, uploads and the private
configuration. Change `GROVS_VERSION`, review/apply, deploy the API and confirm
migrations, then restart workers and dashboard with the matching release.

Deleting services or volumes can delete data. Export your databases and review
the deletion plan. Removing a Railway project does not remove an external S3
bucket or its charges.
