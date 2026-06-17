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
- **Eight DNS records** pointing at the host (see [DNS](#dns)), ports 80/443 open.
- About **4 vCPU / 8 GB RAM** is a comfortable floor.

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

Point all eight at your server (the backend routes by subdomain):

| Env var | Example | Serves |
|---------|---------|--------|
| `DASHBOARD_HOST` | `dashboard.example.com` | Dashboard UI |
| `API_HOST` | `api.example.com` | Dashboard API |
| `SDK_HOST` | `sdk.example.com` | **Mobile SDKs** |
| `MCP_HOST` | `mcp.example.com` | MCP OAuth/API |
| `GO_HOST` | `go.example.com` | Short-link helper |
| `LINKS_PROD_HOST` | `links.example.com` | Production links |
| `LINKS_TEST_HOST` | `test-links.example.com` | Test links |
| `PREVIEW_HOST` | `preview.example.com` | Link previews |

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
