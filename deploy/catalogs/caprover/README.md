# CapRover One Click App package

`grovs.yml` is a candidate for [CapRover One Click Apps](https://github.com/caprover/one-click-apps).
It uses CapRover's supported service fields rather than importing the standalone
Compose stack. Its metadata uses `isOfficial` because the images come from Grovs
and the database publishers; this does not mean the catalog has accepted it.
Live deployment and wildcard HTTPS checks are pending.

## Prepare and validate the submission

Regenerate from the self-host root with
`python3 scripts/generate-panel-catalogs.py`. In a checkout of the upstream
repository, copy `grovs.yml` to `public/v4/apps/grovs.yml` and `grovs.png` to
`public/v4/logos/grovs.png`, then run:

```bash
npm ci
npm run validate_apps
npm run build
```

Use CapRover's custom One Click App template input to deploy the file and finish
the steps below. Before opening an upstream PR, format the copied file with
upstream Prettier, test the [fresh-install scenarios](../README.md) and record
the deployed versions. The upstream validator checks metadata; it does not run
Grovs or verify migrations and HTTPS.

## Installation inputs

Use one server with at least 4 vCPU / 8 GB RAM / 80 GB SSD, a domain you control
and a private S3-compatible bucket. Enter:

- An app base domain, for example `grovs.example.com`.
- Production links domain, for example `links.example.com`.
- Test links domain, for example `test.links.example.com`.
- Your first administrator email and bucket credentials, region and bucket name.
  Leave the endpoint empty for AWS S3; supply the provider's HTTPS endpoint otherwise.

Leave the generated database, OAuth, encryption and administrator secrets in
place and save them securely. Each field is reused by the services that need it.
Do not generate replacement secrets for an existing installation.

## Attach domains before login

In CapRover's HTTP settings, use container port 3000 for web and dashboard.
Point DNS at the CapRover server and attach these custom domains:

| Service | Hosts |
|---|---|
| Dashboard | `dashboard.<app domain>` |
| Web | `api`, `sdk`, `mcp`, `go`, `preview` under the app domain |
| Web | `links.<production links domain>`, `links.<test links domain>` |
| Web | `*.<production links domain>`, `*.<test links domain>` |

Enable HTTPS for each fixed domain. Supply wildcard certificates through your
panel's certificate configuration and configure wildcard host routing to web.
DNS wildcard records alone do not enable wildcard HTTPS. Verify a new project's
production and test hosts, including mobile association files, before sharing
links. This configuration still needs a live CapRover test.

## Startup, credentials and updates

Web waits for the databases, runs Rails migrations, seeds the first admin/OAuth
client and prepares ClickHouse before starting the API. Workers wait for web's
health endpoint. Read logs to distinguish migration failures from pending DNS.
Sign in at `https://dashboard.<app domain>` with `BOOTSTRAP_ADMIN_EMAIL` and
`BOOTSTRAP_ADMIN_PASSWORD` from the web application's environment.

Keep one replica of each service and replace workers by stopping the existing
instance before starting its replacement. In particular, `worker-1` contains the
scheduler. Databases have private networking and persistent volumes. Back up
databases, the bucket and all environment secrets before upgrading. Stop workers,
update both Grovs images to the same version, let web finish migrations and
become healthy, then restart workers and dashboard. Preserve the three database
volumes and secrets; do not reinstall the template over an existing deployment.

Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
