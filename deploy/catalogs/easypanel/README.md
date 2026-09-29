# Easypanel template package

For installation, start with the [Easypanel setup guide](../../../docs/deploy/easypanel.md).

`grovs/` is a native template candidate for the
[Easypanel template repository](https://github.com/easypanel-io/templates).
It generates seven services from public Grovs images and official database
images. It has passed local schema and secret-sharing checks and was installed
on an Easypanel instance: migrations, login, fixed hosts with HTTPS, shared
uploads and project links through wildcard domains. Wildcard certificates through
a DNS challenge on a real domain have not been verified yet.

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
inputs. Import it into an Easypanel instance and complete the
steps below. `grovs/assets/screenshot.png` was captured from the live test
instance with demo data. Before an upstream PR, run upstream formatting and
`npm run build`.

## Installation inputs

Start with one server with 4 vCPU / 8 GB RAM / 80 GB SSD. Provide the app base
domain, production links domain,
test links domain and first admin email. For example:

| Input | Example |
|---|---|
| App base domain | `grovs.example.com` |
| Production links domain | `links.example.com` |
| Test links domain | `test.links.example.com` |

Uploads are stored in the web service's `storage` volume, which Easypanel
keeps in a folder under `/etc/easypanel/projects`. Both workers bind that
folder, so all three see the same files. To use a
private S3-compatible bucket instead, enter its region, name, access key and
secret; the template then switches all services to S3. Leave the endpoint empty
for AWS S3, or enter the provider's HTTPS endpoint for another compatible
service. Uploads are served through the Grovs API either way.

Database, encryption, admin and OAuth secrets are generated once and shared by
the appropriate services. Save the generated configuration securely. Reopening
the generator creates new secrets; do not use it to update an existing install.

## Domains and HTTPS

The template attaches `dashboard.<app domain>` to the dashboard and `api`, `sdk`,
`mcp`, `go` and `preview` under the app domain to web, all on container port 3000.
Point their DNS records at the Easypanel server.

It also attaches the production and test links domains to web as wildcard
domains. Those route every project host, including `links.<links domain>`, with
a lower priority than the fixed hosts. Point both wildcard DNS records at the
server.

Wildcard certificates need a DNS challenge. Until one is set up, project hosts
work but Traefik serves its self-signed Easypanel certificate on them. Create a
DNS challenge resolver following Easypanel's
[wildcard domain guide](https://easypanel.io/docs/guides/wildcard-domain), then
select it in the SSL tab of both wildcard domains on web. Test a newly created
project's production and test host over HTTPS, including its mobile
association files.

## Startup and operation

Web waits for PostgreSQL and ClickHouse, runs migrations, bootstrap seeds and
ClickHouse setup, then starts the API. Workers wait for the web health endpoint.
Check service logs if the API does not become ready. Sign in at the dashboard
using `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from web's environment.

Keep every service at one replica and zero-downtime replacement disabled.
Database services have persistent volumes and no public port mappings. For
upgrades, stop workers, update both application images to the same release,
restart web and wait for successful migrations, then restart workers/dashboard.
Preserve all secrets and volumes. Back up the databases, the uploads volume or
bucket, and the configuration before an upgrade.

Deleting the project in Easypanel can leave its services, network, volumes and
folder under `/etc/easypanel/projects` behind. A new project with the same name
then fails with "network with name easypanel-<project> already exists". Remove
the leftovers with `docker service rm`, `docker network rm` and
`docker volume rm`, or use a different project name.

Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
