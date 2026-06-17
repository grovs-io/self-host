# Grovs — Self-Hosted

Run your own [Grovs](https://grovs.io) instance — deep linking, attribution, and
analytics — with Docker Compose. One repo brings up the backend, dashboard,
PostgreSQL, Redis, MinIO (S3-compatible storage), background workers, and a
reverse proxy.

The application code is pulled from two git submodules:

| Submodule    | Repo                                            |
|--------------|-------------------------------------------------|
| `backend/`   | [grovs-io/backend](https://github.com/grovs-io/backend)   |
| `dashboard/` | [grovs-io/dashboard](https://github.com/grovs-io/dashboard) |

Everything self-hosted is **off by default** in those repos and only activates
when `GROVS_SELF_HOSTED=true` (backend) / `NEXT_PUBLIC_SELF_HOSTED=true`
(dashboard) — which this stack sets for you.

---

## What runs

| Service | Description |
|---------|-------------|
| `proxy` | Caddy reverse proxy + automatic TLS (standalone only) |
| `postgres` | PostgreSQL 16 |
| `redis` | Redis 7 (AOF persistence, no eviction) |
| `minio` (+ `minio-setup`) | S3-compatible object storage + bucket creation |
| `backend-migrate` | One-shot: DB migrate + seed (creates the OAuth app + your admin) |
| `backend-web-1`, `backend-web-2` | Rails API (Puma) |
| `backend-worker-1` | Sidekiq: scheduler + events + batch — **singleton, never scale** |
| `backend-worker-2` | Sidekiq: maintenance + device updates |
| `dashboard` | Next.js dashboard |

---

## Prerequisites

- A Linux host with **Docker + Docker Compose v2**.
- **Two registrable domains** (production + test) with the reserved-host and **wildcard**
  records pointing at the host (see [DNS](#dns)), ports 80/443 open.
- About **4 vCPU / 8 GB RAM** is a comfortable floor.

---

## Capacity & scaling

This single-host Docker Compose stack runs the **entire platform on one machine**
(PostgreSQL, Redis, MinIO, two web replicas, two worker replicas, dashboard, proxy). On
the recommended hardware below it comfortably handles a deep-linking / attribution
workload of roughly **150,000–200,000 monthly users**.

**Beyond ~200k users you'll outgrow a single box** and should move to a **custom
deployment + infrastructure**: managed/replicated PostgreSQL, a dedicated Redis,
external object storage (e.g. AWS S3), and horizontally-scaled web/worker nodes behind a
load balancer. The same images and environment variables still apply — you split the
services across hosts and point the connection strings (`DATABASE_URL`, `REDIS_URL`,
`S3_*`) at the managed services. [Reach out](https://grovs.io) if you need help sizing a
larger deployment.

### Recommended server

Tested baseline (what this guide is validated on):

| | |
|---|---|
| Provider | Hetzner Cloud (any VPS or bare-metal works) |
| Type | **CX33-class** (shared vCPU) or better |
| CPU / RAM | **4 vCPU / 8 GB RAM** floor — 8 vCPU / 16 GB for headroom |
| Disk | **80 GB+ SSD** (Postgres + MinIO uploads grow over time) |
| OS | Ubuntu 22.04 / 24.04 LTS with Docker + Compose v2 |
| Network | Public IPv4, ports **80 + 443** open, wildcard DNS `*.yourdomain` |

As you add CPU/RAM, raise `WEB_CONCURRENCY`, `RAILS_MAX_THREADS`,
`SIDEKIQ_EVENTS_CONCURRENCY`, and `POSTGRES_MAX_CONNECTIONS` (see the
[environment reference](#environment-variables)).

---

## Deploy — Option A: standalone (any VPS)

```bash
# 1. Clone with submodules
git clone --recursive https://github.com/grovs-io/self-hosted.git grovs-self-hosted
cd grovs-self-hosted          # (if you forgot --recursive: git submodule update --init)

# 2. Generate secrets (.env) — prints your admin password
./scripts/setup.sh

# 3. Set your domains
$EDITOR .env
#   set every *_HOST, ACME_EMAIL, BOOTSTRAP_ADMIN_EMAIL
#   set SERVER_HOST / REACT_HOST / S3_ASSET_PREFIX to your API + dashboard hosts

# 4. Build and start (the proxy runs only with the 'standalone' profile)
docker compose --profile standalone build
docker compose --profile standalone up -d
```

Open `https://<DASHBOARD_HOST>` and log in with `BOOTSTRAP_ADMIN_EMAIL` + the
password from step 2. No SMTP or SSO required.

---

## Deploy — Option B: Coolify

[Coolify](https://coolify.io) provides its own reverse proxy and TLS, so the
bundled Caddy `proxy` is skipped automatically (it's behind the `standalone`
profile). You assign domains to services in Coolify instead.

1. **Push this repo** to a Git provider Coolify can read (e.g. your own
   `self-hosted` repo). Submodules must be reachable.
2. In Coolify: **+ New → Resource → Docker Compose**, choose your repo/branch.
   - In the source settings, enable **Git Submodules** (pulls `backend` + `dashboard`).
   - Compose file: `docker-compose.yml`.
3. **Environment variables:** open the resource's **Environment Variables**, paste
   the contents of `.env.example`, and fill in the values. Generate the secrets
   first by running `./scripts/setup.sh` locally and copying them, or generate your
   own. Make sure these match:
   - `NEXT_PUBLIC_CLIENT_ID` = `OAUTH_CLIENT_UID`, `CLIENT_SECRET` = `OAUTH_CLIENT_SECRET`
   - the password in `DATABASE_URL` = `POSTGRES_PASSWORD`
   - `AWS_S3_KEY_ID`/`AWS_S3_ACCESS_KEY` = `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`
   - `NEXT_PUBLIC_API_URL` = `https://<API_HOST>`, `S3_ASSET_PREFIX` = `https://<API_HOST>`
   > `NEXT_PUBLIC_*` are baked into the dashboard **at build time**, so set them
   > before the first deploy (changing them later requires a rebuild).
4. **Domains:** open each service and set its domain(s):
   - `dashboard` → your `DASHBOARD_HOST`
   - `backend-web-1` → all seven backend hosts, comma-separated: `API_HOST, SDK_HOST,
     MCP_HOST, GO_HOST, LINKS_PROD_HOST, LINKS_TEST_HOST, PREVIEW_HOST`
     (the backend routes by subdomain, so they all target `backend-web-1`).

   Point those DNS records at your Coolify server. Coolify issues TLS automatically.
5. **Deploy.** Coolify builds the images and runs the stack; `backend-migrate`
   runs first (migrate + seed), then the web/worker/dashboard services start.
6. Open `https://<DASHBOARD_HOST>` and log in as the bootstrap admin.

---

## DNS

**You need TWO separate registrable domains — one for production, one for test.**

Grovs serves **production** and **test** links from per-project subdomains, and the
backend distinguishes them by their **registrable domain**. So you must use **two
separate registrable domains** — one for production, one for test — exactly like the
hosted service uses `sqd.link` (prod) and `test-sqd.link` (test).

> ⚠️ **The test domain must NOT be a sub-label of the production domain.**
> `DOMAIN_TEST=test-links.example.com` (a subdomain of `example.com`) **will not route** —
> the host parser splits `proj.test-links.example.com` into subdomain `proj.test-links`
> + domain `example.com`, so the test project never matches. Use a **distinct
> registrable domain** such as `example-test.com`.

**Production domain — `DOMAIN_LIVE` (e.g. `example.com`).** Point all of these at your server:

| Env var | Example | Serves |
|---------|---------|--------|
| `DASHBOARD_HOST` | `dashboard.example.com` | Dashboard UI |
| `API_HOST` | `api.example.com` | Dashboard API + asset blobs |
| `SDK_HOST` | `sdk.example.com` | **Mobile/server SDKs** (the SDK `baseURL`) |
| `MCP_HOST` | `mcp.example.com` | MCP OAuth/API |
| `GO_HOST` | `go.example.com` | Short-link helper |
| `LINKS_PROD_HOST` | `links.example.com` | Production links |
| `PREVIEW_HOST` | `preview.example.com` | Link previews |
| `*.example.com` (**wildcard**) | `*.example.com` | Per-project **production** link subdomains |

**Test domain — `DOMAIN_TEST` (a _separate_ registrable domain, e.g. `example-test.com`):**

| Env var | Example | Serves |
|---------|---------|--------|
| `LINKS_TEST_HOST` | `links.example-test.com` | Test links |
| `*.example-test.com` (**wildcard**) | `*.example-test.com` | Per-project **test** link subdomains |

A **wildcard** record on each domain is required — every project gets its own random
link subdomain. The standalone Caddy proxy issues TLS on demand for those; for reliable
Universal Links / App Links, prefer a **pre-issued wildcard certificate** (via your DNS
provider's API) so Apple/Google can fetch the association files without a TLS cold-start.

---

## Verify your deployment

```bash
# Backend health
curl -sS https://<API_HOST>/up           # -> 200

# Bootstrap-admin login returns an access token
curl -s -X POST https://<API_HOST>/oauth/token \
  -d grant_type=password \
  -d email="<BOOTSTRAP_ADMIN_EMAIL>" -d password="<BOOTSTRAP_ADMIN_PASSWORD>" \
  -d client_id="<OAUTH_CLIENT_UID>" -d client_secret="<OAUTH_CLIENT_SECRET>"
```

Then in the dashboard: log in → create a project → create a link → open it. The
project's **API key** is what your SDKs use (next section).

---

## Environment variables

Everything is configured through `.env` (copy from `.env.example`).
`./scripts/setup.sh` generates all the secrets and the OAuth pair for you — you mainly
fill in the **hostnames** and **two domains**. Here is what every variable does.

### Hostnames & TLS
| Variable | What it does |
|----------|--------------|
| `DASHBOARD_HOST` | Hostname of the dashboard UI (Next.js). |
| `API_HOST` | Dashboard / REST API host. Also serves ActiveStorage blobs (proxy mode). |
| `SDK_HOST` | **Mobile + server SDK host** — this exact value is the SDK `baseURL`. |
| `MCP_HOST` | MCP (Model Context Protocol) OAuth/API host. |
| `GO_HOST` | Short-link helper host. |
| `LINKS_PROD_HOST` | Production links host (under `DOMAIN_LIVE`). |
| `LINKS_TEST_HOST` | Test links host (under `DOMAIN_TEST`). |
| `PREVIEW_HOST` | Link-preview host. |
| `ACME_EMAIL` | Email Let's Encrypt uses for cert-expiry notices (standalone proxy only). |

### Self-hosted flags
| Variable | What it does |
|----------|--------------|
| `GROVS_SELF_HOSTED` | Master switch — **must be `true`**. Disables Stripe/billing & public sign-ups, turns member invites into copyable links (no SMTP needed), enables ActiveStorage proxy mode. |
| `GROVS_EE` | Enterprise edition (in-app-purchase / revenue features). Leave `false` unless licensed. |
| `FREE_MAU_COUNT` | Monthly-active-user quota cap. Self-hosted = effectively unlimited (`999999999`). |
| `FREE_PASS_PROJECT_IDS` | Comma-separated project IDs exempt from quotas. Usually empty. |

### PostgreSQL
| Variable | What it does |
|----------|--------------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credentials + database name for the bundled Postgres. |
| `POSTGRES_MAX_CONNECTIONS` | Server-side connection ceiling. Keep ≥ (web replicas × `RAILS_DB_POOL`) + worker pools. |
| `DATABASE_URL` | Connection string Rails uses. **Password must match `POSTGRES_PASSWORD`.** Point at a managed Postgres for a custom deployment. |

### Redis
| Variable | What it does |
|----------|--------------|
| `REDIS_URL` | Redis connection — event queues, caches, dedup, fingerprints. |

### Process sizing (tune to host capacity)
| Variable | What it does |
|----------|--------------|
| `WEB_CONCURRENCY` | Puma worker processes per web container. |
| `RAILS_MAX_THREADS` | Threads per Puma worker. |
| `RAILS_DB_POOL` | DB connection pool per process. |
| `SIDEKIQ_EVENTS_CONCURRENCY` | Threads for the events worker. |

### Object storage (bundled MinIO, or your S3)
| Variable | What it does |
|----------|--------------|
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | Admin credentials for the bundled MinIO. |
| `AWS_S3_KEY_ID` / `AWS_S3_ACCESS_KEY` | S3 credentials — **must equal the MinIO creds** for the bundled setup (or your AWS keys). |
| `AWS_S3_REGION` / `AWS_S3_BUCKET` | Region + bucket name. |
| `S3_ENDPOINT` | S3 endpoint. `http://minio:9000` for bundled MinIO; leave **empty** for real AWS S3. |
| `S3_FORCE_PATH_STYLE` | `true` for MinIO (path-style URLs). |
| `S3_ASSET_PREFIX` | Public URL prefix for blobs — point at `https://<API_HOST>` (proxy mode serves them through the backend). |

### Rails core & secrets
| Variable | What it does |
|----------|--------------|
| `RAILS_ENV` | `production`. |
| `RAILS_LOG_TO_STDOUT` | `true` so Docker captures logs. |
| `RAILS_SERVE_STATIC_FILES` | `true` — the backend serves its own compiled assets. |
| `SECRET_KEY_BASE` | Rails session/signing secret. **Generate once, keep stable.** |
| `ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY`, `_DETERMINISTIC_KEY`, `_KEY_DERIVATION_SALT` | At-rest encryption keys. **Generate once; never change after data exists** — rotating them makes encrypted columns unreadable. |
| `ADMIN_API_KEY` | Key guarding internal admin endpoints. |
| `DIAGNOSTICS_API_KEY` | Key guarding diagnostics endpoints. |
| `SENT_QUOTAS_WEBHOOK_KEY` | Key for the quota-reporting webhook. |
| `PUBLIC_GO_PROJECT_IDENTIFIER` | Identifier for the built-in `go` redirect project (seeded automatically). |
| `DEFAULT_LOGO_URL` | App icon shown on link landing pages when a project has no app-store icon. Set to your own logo to rebrand. |
| `DEFAULT_SOCIAL_PREVIEW_URL` | OG/Twitter preview image used when a link has no custom preview image. |
| `DEFAULT_LINK_TITLE` / `DEFAULT_LINK_SUBTITLE` | Default OG title / description for link previews. |

### Link & redirect hosts (the two domains)
| Variable | What it does |
|----------|--------------|
| `SERVER_HOST_PROTOCOL` / `SERVER_HOST` | Protocol + host the backend uses to build absolute URLs — your API host. |
| `REACT_HOST_PROTOCOL` / `REACT_HOST` | Protocol + host for dashboard links (e.g. in emails) — your dashboard host. |
| `DOMAIN_LIVE` | **Production base / registrable domain** (e.g. `example.com`) — **NOT a subdomain**. All reserved hosts and per-project prod link subdomains are children of it; routing only works when this is the registrable base. |
| `DOMAIN_TEST` | **Test base domain — a _separate_ registrable domain** (e.g. `example-test.com`). ⚠️ Must **not** be a sub-label of `DOMAIN_LIVE` (e.g. `test-links.example.com`), or test links won't route. |
| `PREVIEW_BASE_URL` | Full URL of the preview host. |
| `MCP_CONSENT_URL` | OAuth consent URL for MCP. |

### OAuth (dashboard login)
| Variable | What it does |
|----------|--------------|
| `OAUTH_CLIENT_UID` / `OAUTH_CLIENT_SECRET` | Doorkeeper "React" app credentials; the seed upserts the app to these. |
| `NEXT_PUBLIC_CLIENT_ID` | **Must equal `OAUTH_CLIENT_UID`.** Baked into the dashboard at build time. |
| `CLIENT_SECRET` | **Must equal `OAUTH_CLIENT_SECRET`.** Used by the dashboard's server-side token route. |

### Dashboard (baked at build time)
> These `NEXT_PUBLIC_*` values are compiled **into the dashboard image** — changing them later requires a rebuild.

| Variable | What it does |
|----------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://<API_HOST>` — where the dashboard calls the API. |
| `NEXT_PUBLIC_API_PATH` | API path prefix, `/api/v1`. |
| `NEXT_PUBLIC_ENV` | `production`. |
| `NEXT_PUBLIC_SELF_HOSTED` | `true` — hides SaaS-only/billing UI, enables the invite-link flow. |

### First-run admin
| Variable | What it does |
|----------|--------------|
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | The seed creates this admin so you can log in with no SMTP/SSO. After login you're prompted to create your first project. |

### Email (optional)
| Variable | What it does |
|----------|--------------|
| `MAILER_DELIVERY_METHOD` | Leave **empty** to disable email entirely. Set to `smtp` to enable password-reset + data-export emails. |
| `SMTP_ADDRESS` / `SMTP_PORT` / `SMTP_DOMAIN` | SMTP server address, port, HELO domain. |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP authentication. |
| `SMTP_AUTHENTICATION` | `plain`, `login`, or `cram_md5`. |
| `SMTP_ENABLE_STARTTLS_AUTO` | `true` to use STARTTLS when available. |
| `MAILER_FROM` | From address for outgoing email. |

---

## Configure the SDKs

The mobile SDKs talk to your **SDK host** (`SDK_HOST`). Pass it as the base URL when
you initialize, and use your project's API key from the dashboard.

**iOS** ([grovs-io/grovs-iOS](https://github.com/grovs-io/grovs-iOS))

```swift
import Grovs

Grovs.configure(
    APIKey: "YOUR_PROJECT_API_KEY",
    useTestEnvironment: false,
    baseURL: "https://sdk.example.com",   // your SDK_HOST — SDK appends the API path
    delegate: self
)
```

**Android** ([grovs-io/grovs-android](https://github.com/grovs-io/grovs-android))

The Android SDK takes the same self-hosted base URL — set it to `https://<SDK_HOST>`
in the `Grovs.configure(...)` call (see the repo README for the exact signature):

```kotlin
Grovs.configure(
    application = this,
    apiKey = "YOUR_PROJECT_API_KEY",
    useTestEnvironment = false,
    baseURL = "https://sdk.example.com"   // your SDK_HOST
)
```

Server-to-server callers use the same host with the `PROJECT-KEY` + `ENVIRONMENT`
headers against `https://<SDK_HOST>`.

> **Always pass `baseURL` in _every_ `configure(...)` call — including release/production
> builds.** If you omit it (common in a `#else` / release branch), the SDK falls back to
> the hosted Grovs cloud (`sqd.link`) and your self-hosted links won't resolve. Also match
> `useTestEnvironment` to the API key's environment: **test key → `true`**, **production
> key → `false`**. A production link opened by a test-mode app (or vice-versa) won't
> resolve its payload.

> **Universal Links / App Links need the matching domains in the app, too.** Add
> `applinks:*.<DOMAIN_LIVE>` **and** `applinks:*.<DOMAIN_TEST>` to the iOS app's Associated
> Domains (and the Android `assetlinks` equivalent), then reinstall — iOS caches the
> association at install time.

---

## Email (optional)

Email is off by default. The bootstrap admin needs none, and member invites produce
a copyable link (no email sent). Set `MAILER_DELIVERY_METHOD=smtp` and the `SMTP_*`
vars only if you want **password reset** or **data-export** emails.

---

## Upgrades

```bash
git submodule update --remote --merge        # pull latest backend + dashboard
docker compose --profile standalone build
docker compose run --rm backend-migrate      # migrate BEFORE restarting web/workers
docker compose --profile standalone up -d
```

On Coolify, bump the submodules in your repo and redeploy.

## Backups

Durable state lives in named volumes:
- **`pg_data`** — the system of record. Back it up (`pg_dump` off-box / volume snapshots).
- **`minio_data`** — uploaded assets and exports (`mc mirror` or snapshot).
- **`redis_data`** — AOF; only undrained events are at risk.
