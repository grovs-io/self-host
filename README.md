# Grovs — Self-Hosted

Run your own [Grovs](https://grovs.io) instance — deep linking, attribution, and
analytics — with Docker Compose. One directory brings up the backend, dashboard,
PostgreSQL, Redis, ClickHouse, background workers, and a reverse proxy with
automatic TLS, all from published images.

Images: `ghcr.io/grovs-io/backend` and `ghcr.io/grovs-io/dashboard`, released together
under one version (`GROVS_VERSION`). Source: [grovs-io/backend](https://github.com/grovs-io/backend),
[grovs-io/dashboard](https://github.com/grovs-io/dashboard).

---

## What runs

| Service | Description |
|---------|-------------|
| `proxy` | Caddy reverse proxy + automatic TLS (standalone profile only) |
| `postgres` | PostgreSQL 16 |
| `redis` | Redis 7 (AOF persistence, no eviction) |
| `clickhouse` | ClickHouse 25.3, the analytics and event store |
| `migrate` | One-shot on every start: migrates PostgreSQL + ClickHouse, seeds the OAuth app + your admin |
| `web` | Rails API (Puma) |
| `worker-1` | Sidekiq: scheduler + events + batch — **singleton, never scale** |
| `worker-2` | Sidekiq: maintenance + device updates |
| `dashboard` | Next.js dashboard, configured at start from `.env` |

Uploads live in the `storage` volume and are served through the API host; set
`ACTIVE_STORAGE_SERVICE=amazon` plus the `AWS_S3_*` variables to use S3 instead.

---


## Prerequisites

- A Linux host with **Docker + Docker Compose v2**, ports 80/443 open.
- **One domain** you control, with the records in [DNS](#dns) pointing at the host.
- About **4 vCPU / 8 GB RAM** is a comfortable floor.

---

## Capacity & scaling

This single-host Docker Compose stack runs the **entire platform on one machine**
(PostgreSQL, Redis, ClickHouse, web, two workers, dashboard, proxy). On
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
| Disk | **80 GB+ SSD** (PostgreSQL, ClickHouse and uploads grow over time) |
| OS | Ubuntu 22.04 / 24.04 LTS with Docker + Compose v2 |
| Network | Public IPv4, ports **80 + 443** open, wildcard DNS `*.yourdomain` |

As you add CPU/RAM, raise `WEB_CONCURRENCY`, `RAILS_MAX_THREADS`,
`SIDEKIQ_EVENTS_CONCURRENCY`, and `POSTGRES_MAX_CONNECTIONS` (see the
[environment reference](#environment-variables)).

---

## Deploy

One command, once DNS points at the host (see [DNS](#dns)):

```bash
curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/main/install.sh | bash
```

It downloads the stack into `./grovs`, asks for your app domain, links domain, test links
domain and admin email (Enter accepts each default, see [DNS](#dns)), generates every secret, pulls the images and starts the stack with
the `standalone` proxy. Read [install.sh](install.sh) first if you prefer; the manual
equivalent is:

```bash
git clone https://github.com/grovs-io/self-host.git grovs && cd grovs
./scripts/setup.sh                              # writes .env: domains + secrets, prints your admin password
docker compose --profile standalone up -d       # drop the profile on platforms with their own proxy
```

Open `https://<DASHBOARD_HOST>` and log in with the admin email + password printed by
setup. No SMTP or SSO required. Certificates are issued on the first request to each host.

---


## Try it on your machine first

No domain, no DNS, no TLS. Run the installer and press Enter at the first prompt:

```bash
curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/main/install.sh | bash
```

It starts the same stack on `lvh.me`, a public name that resolves to `127.0.0.1`, with the
dashboard at `http://dashboard.lvh.me:3002` and the API at `http://api.lvh.me`. Log in with
the printed admin password, create a project and a link, open it. Real deep links into apps
need a real domain, everything else works. Change the ports with `GROVS_WEB_PORT` and
`GROVS_DASHBOARD_PORT` before running it. Remove it with
`docker compose -f docker-compose.yml -f docker-compose.local.yml down -v` in the install dir.

Works on Linux and macOS with Docker, and on Windows through WSL2 with Docker Desktop.

---

## DNS

Grovs uses up to three domains, and the installer asks for them in this order, each with a
default you can accept by pressing Enter:

| Prompt | Env | What lives there | Default |
|--------|-----|------------------|---------|
| App domain | `SERVER_HOST` | `dashboard.`, `api.`, `sdk.`, `go.`, `mcp.`, `preview.` | local trial on `lvh.me` |
| Links domain | `DOMAIN_LIVE` | production links: `<project>.<links domain>` | the app domain |
| Test links domain | `DOMAIN_TEST` | test-environment links | `test.<links domain>` |

A branded short domain for links (`acme.link`) next to the company domain for the app
(`acme.com`) is the usual setup; one domain for everything also works.

All records are `A` records → your server's IPv4 (add matching `AAAA` if it has IPv6):

| Domain | Name (host) | Serves |
|--------|-------------|--------|
| app | `dashboard`, `api`, `sdk`, `go`, `mcp`, `preview` | the fixed hosts above |
| links | **`*`** (wildcard) | per-project production links, e.g. `a1b2c3d4.acme.link` |
| links | `links` | `LINKS_PROD_HOST`, pre-issued certificate |
| test links | **`*`** (wildcard) | per-project test links, e.g. `a1b2c3d4.test.acme.link` |
| test links | `links` | `LINKS_TEST_HOST`, pre-issued certificate |

With one domain for everything that is the six fixed hosts plus `*` and `*.test` on it.

> **TLS / Universal Links.** The standalone Caddy proxy issues certificates **on demand**
> for each new subdomain (first hit takes a few seconds). For reliable **Universal Links /
> App Links**, pre-issue wildcard certificates for the links and test-links domains via
> your DNS provider's API; otherwise Apple's/Google's association fetcher can time out on
> the cold start and cache the failure for about an hour. Behind Cloudflare, keep the link
> records **DNS-only (grey cloud)** so Caddy terminates TLS, or use a Cloudflare Origin cert.

---

## After install: changing settings

Everything is configured by `.env` in the install directory (`./grovs`). Edit it, then apply:

```bash
docker compose --profile standalone up -d                                   # real domain
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d      # local trial
```

Compose restarts only the containers whose environment changed; the database, uploads and
analytics stay. Two rules: never change the generated secrets (`SECRET_KEY_BASE`, the
`ACTIVE_RECORD_ENCRYPTION_*` keys, the database and ClickHouse passwords) after the first
start, the existing data is bound to them; and if you change a domain, update DNS first.

### Optional features

Off by default. Each is a few lines in `.env` followed by the `up -d` above.

**Custom domains** let a project serve links on a domain your customer owns
(`links.customer.com`) instead of `<project>.<links domain>`:

```
CUSTOM_DOMAINS_ENABLED=true
CUSTOM_DOMAINS_PROVIDER=manual
SELF_HOSTED_INGRESS_HOST=links.acme.link     # the host customers point their CNAME at; defaults to SERVER_HOST
```

Then, per domain: the customer creates `CNAME links.customer.com → <SELF_HOSTED_INGRESS_HOST>`,
an admin adds the domain on the project's Domain page, and Grovs verifies it within a minute
by probing `https://links.customer.com/.well-known/grovs-domain-verification`. The bundled
proxy issues the certificate on that first request; behind your own proxy, attach a
certificate for the host before the customer flips DNS.

**Migrate from Branch or AppsFlyer** resolves an old short link upstream on its first click,
creates the equivalent Grovs link, and redirects; later clicks never touch the old provider:

```
MIGRATIONS_ENABLED=true
```

Then set the migration up on the project's Domain page with the provider credentials. Custom
domains must be enabled too when the old links live on a domain you will point at Grovs.

**Email** for invites, password resets and exports: fill in the `SMTP_*` block and set
`MAILER_DELIVERY_METHOD=smtp`. Without it, admins invite members with a copyable link.

**Uploads on S3** instead of the local volume: `ACTIVE_STORAGE_SERVICE=amazon` plus the
`AWS_S3_*` variables (and `S3_ENDPOINT` + `S3_FORCE_PATH_STYLE=true` for S3-compatible stores).

**Analytics on the first minute.** A fresh install shows "Analytics temporarily unavailable"
until the first rollup run completes, about a minute after boot. Reload.

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
| `GROVS_SELF_HOSTED` | Master switch — **must be `true`**. Disables Stripe/billing & public sign-ups, removes MAU quotas, turns member invites into copyable links (no SMTP needed), enables ActiveStorage proxy mode. |
| `GROVS_EE` | Enterprise edition (in-app-purchase / revenue features). Leave `false` unless licensed. |

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

### Uploads
| Variable | What it does |
|----------|--------------|
| `ACTIVE_STORAGE_SERVICE` | `local` (default) keeps uploads in the `storage` volume; `amazon` uses S3 with the `AWS_S3_*` variables (`S3_ENDPOINT` + `S3_FORCE_PATH_STYLE=true` for S3-compatible stores). |
| `S3_ASSET_PREFIX` | Public URL prefix for uploads — `https://<API_HOST>`; they are served through the backend. |

### ClickHouse
| Variable | What it does |
|----------|--------------|
| `CLICKHOUSE_PASSWORD` | Password of the `grovs` ClickHouse user (generated by setup). |
| `CLICKHOUSE_*_ENABLED`, `CLICKHOUSE_PRIMARY`, `CLICKHOUSE_ROLLUP_FAST_LANE`, `REVENUE_READS_FROM_LEDGER`, `PG_SHADOW_WRITES` | ClickHouse is the event store and serves every analytics read; PostgreSQL keeps a spill fallback only. Leave them as shipped. |


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
| `SERVER_HOST_PROTOCOL` / `SERVER_HOST` | Protocol + the bare production domain (`example.com`); the `api.`/`sdk.`/`go.`/`preview.` hosts derive from it. Never the `api.` host itself: boot refuses it. |
| `REACT_HOST_PROTOCOL` / `REACT_HOST` | Protocol + host for dashboard links (e.g. in emails) — your dashboard host. |
| `DOMAIN_LIVE` | **Production base / registrable domain** (e.g. `example.com`) — **NOT a subdomain**. All reserved hosts and per-project prod link subdomains are children of it; routing only works when this is the registrable base. |
| `DOMAIN_TEST` | Base domain for test-environment links, `test.<DOMAIN_LIVE>` by default. A separate registrable domain also works. |
| `PREVIEW_BASE_URL` | Full URL of the preview host. |
| `MCP_CONSENT_URL` | OAuth consent URL for MCP. |

### OAuth (dashboard login)
| Variable | What it does |
|----------|--------------|
| `OAUTH_CLIENT_UID` / `OAUTH_CLIENT_SECRET` | Doorkeeper "React" app credentials. The seed upserts the app to them and the dashboard reads the same pair at start. |


### Dashboard
The dashboard image is generic: `docker-compose.yml` hands it `API_URL` (from `API_HOST`)
and the OAuth pair at start. Nothing is baked in, so upgrading is pulling a new image.


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

## Branding & link images

Link landing pages and social/link previews pull images from two places: **per-project /
per-link images you set in the dashboard**, and **fallback defaults** for when a link has
none. Set both up so links never render blank.

### Default images (env) — so nothing is ever empty

If a project has no app-store icon and a link has no custom preview image, Grovs falls
back to these. They ship pointing at the Grovs assets; **set your own URLs to rebrand:**

| Variable | Used for |
|----------|----------|
| `DEFAULT_LOGO_URL` | App icon on the link landing page when a project has no app-store icon. |
| `DEFAULT_SOCIAL_PREVIEW_URL` | OG / Twitter card image when a link has no custom preview image. |
| `DEFAULT_LINK_TITLE` | Default `og:title` for link previews. |
| `DEFAULT_LINK_SUBTITLE` | Default `og:description` for link previews. |

> ⚠️ **Leave these empty and link pages show a blank icon and social shares render an
> empty card** (no image, no title) — point them at publicly reachable image URLs. A
> **1200×630** JPG/PNG works well for the social preview.

### Uploaded images (dashboard) — must be reachable

App icons and per-link preview images you upload in the dashboard are stored in object
storage (the `storage` volume or S3) and served back through the **API host** in proxy mode. For them to
appear on link pages and in social previews:

- **`S3_ASSET_PREFIX` must point at your API host** (`https://<API_HOST>`), and that host
  must be publicly reachable over HTTPS. A wrong `S3_ASSET_PREFIX` is the usual cause of
  "uploaded image doesn't show".
- A per-link image set in the dashboard **overrides** the env defaults above.

### Social-preview caching

Facebook, LinkedIn, iMessage, WhatsApp, etc. **cache** OG data aggressively. If a link
you already shared still looks blank after you fix the image, **re-scrape** it (e.g.
Facebook's Sharing Debugger) or test with a **fresh** link — the cache won't refresh on
its own for a while.

---

## Email (optional)

Email is off by default. The bootstrap admin needs none, and member invites produce
a copyable link (no email sent). Set `MAILER_DELIVERY_METHOD=smtp` and the `SMTP_*`
vars only if you want **password reset** or **data-export** emails.

---

## Upgrades

```bash
# bump GROVS_VERSION in .env, then
docker compose --profile standalone pull
docker compose --profile standalone up -d     # migrate runs first, web and workers restart on the new image
```

Or re-run `install.sh` with `GROVS_VERSION=<new>`; it keeps your `.env`.


## Backups

Durable state lives in named volumes:
- **`pg_data`** — the system of record: projects, links, users, purchases. Back it up (`pg_dump` off-box or volume snapshots).
- **`clickhouse_data`** — events and analytics. Snapshot the volume or use `clickhouse-backup`.
- **`storage`** — uploaded images and exports.
- **`redis_data`** — AOF; only undrained events are at risk.
