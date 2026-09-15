# Deploy on Railway

The repository includes a native
[Railway infrastructure definition](../../.railway/railway.ts). It creates the
API, dashboard, two workers and three private database services with persistent
volumes. It also declares the app and wildcard link domains. You use Railway's
CLI to review the proposed resources before creating them.

**Railway compute, volumes, network usage and your object storage are billable.**
Check your plan's capacity and custom-domain allowance for this seven-service
deployment.

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

Create a private S3 bucket and add these values to the same file (uncomment their
example lines):

```dotenv
AWS_S3_KEY_ID=your-access-key
AWS_S3_ACCESS_KEY=your-secret-key
AWS_S3_REGION=your-bucket-region
AWS_S3_BUCKET=your-bucket-name
```

Use bucket-scoped access for listing, reading, writing and deleting Grovs
objects. S3-compatible storage also accepts `S3_ENDPOINT` and
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
supplies, including certificate verification CNAMEs.

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
