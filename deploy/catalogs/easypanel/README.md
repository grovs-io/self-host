# Easypanel template package

For installation, start with the [Easypanel setup guide](../../../docs/deploy/easypanel.md).

`grovs/` is a native template candidate for the
[Easypanel template repository](https://github.com/easypanel-io/templates).
It generates seven services from public Grovs images and official database
images. It has passed local schema and secret-sharing checks; installation in
an Easypanel instance and wildcard HTTPS verification are still pending.

## Prepare and validate the submission

From the self-host repository, regenerate with
`python3 scripts/generate-panel-catalogs.py`. Copy `grovs/` into `templates/grovs/`
in a checkout of the upstream repository. Use Node 22 for the upstream Next.js 12
playground; its production build fails on Node 26. From that checkout:

```bash
npm ci
npm run build-templates
npx tsc --noEmit
```

Copy this directory's `check-grovs.ts` into the upstream checkout root, then run
`npx ts-node -r tsconfig-paths/register check-grovs.ts`. It validates the generated output against upstream's
schema, shared credentials, distinct credentials between installations,
persistent database volumes and private database services.

Use `npm run dev` to open the playground and generate JSON with your own domain
and private bucket inputs. Import it into an Easypanel instance and complete the
steps below. Before an upstream PR, add an actual populated-dashboard screenshot
to `grovs/assets/`, run upstream formatting and `npm run build`, and record the
live checks from [the package checklist](../README.md). The current package does
not supply fabricated screenshots or claim those live checks passed.

## Installation inputs

Start with one server with 4 vCPU / 8 GB RAM / 80 GB SSD and a private
S3-compatible bucket. Provide the app base domain, production links domain,
test links domain and first admin email. For example:

| Input | Example |
|---|---|
| App base domain | `grovs.example.com` |
| Production links domain | `links.example.com` |
| Test links domain | `test.links.example.com` |

Enter the bucket region, name, access key and secret. Leave the endpoint empty
for AWS S3; enter the provider's HTTPS endpoint for another compatible service.
Use a private bucket: uploads are served through the Grovs API.

Database, encryption, admin and OAuth secrets are generated once and shared by
the appropriate services. Save the generated configuration securely. Reopening
the generator creates new secrets; do not use it to update an existing install.

## Domains and HTTPS

The template attaches `dashboard.<app domain>` to the dashboard and `api`, `sdk`,
`mcp`, `go` and `preview` under the app domain to web, all on container port 3000.
Point their DNS records at the Easypanel server.

Before using project links, add these domains to **web** in Easypanel:

- `links.<production links domain>` and `links.<test links domain>`.
- A wildcard for `*.<production links domain>` and for `*.<test links domain>`.

Point both wildcard DNS records at the server. Configure a wildcard-capable
certificate resolver or install certificates covering both wildcards using
your panel's TLS configuration. A DNS wildcard alone does not supply HTTPS.
Test a newly created project's production and test host over HTTPS, including
its mobile association files. This is the part that still needs verification
on an actual Easypanel installation.

## Startup and operation

Web waits for PostgreSQL and ClickHouse, runs migrations, bootstrap seeds and
ClickHouse setup, then starts the API. Workers wait for the web health endpoint.
Check service logs if the API does not become ready. Sign in at the dashboard
using `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from web's environment.

Keep every service at one replica and zero-downtime replacement disabled.
Database services have persistent volumes and no public port mappings. For
upgrades, stop workers, update both application images to the same release,
restart web and wait for successful migrations, then restart workers/dashboard.
Preserve all secrets and database volumes. Back up the databases, private bucket
and configuration before an upgrade.

Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
