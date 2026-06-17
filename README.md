# Grovs — self-hosted

Run the full Grovs stack (backend, dashboard, Postgres, Redis, MinIO, workers,
reverse proxy) with Docker Compose.

## Prerequisites

- Docker + Docker Compose v2.
- The app code comes from two git submodules, pulled from GitHub:
  - `backend/`   → github.com/grovs-io/backend
  - `dashboard/` → github.com/grovs-io/dashboard
- Eight DNS records pointing at the host (see below), with ports 80/443 reachable
  for automatic TLS.

## Quick start

```bash
git clone --recursive <this-repo> grovs-self-hosted   # pulls backend + dashboard from GitHub
cd grovs-self-hosted
./scripts/setup.sh          # generates .env with strong secrets (prints the admin password)
$EDITOR .env                # set the *_HOST domains, ACME_EMAIL, BOOTSTRAP_ADMIN_EMAIL
docker compose build
docker compose up -d
```

> Already cloned without `--recursive`? Run `git submodule update --init`.

Then open `https://<DASHBOARD_HOST>` and log in with `BOOTSTRAP_ADMIN_EMAIL` and the
password printed by `setup.sh` — no SMTP or SSO required.

## DNS

Point these at the server (the backend routes by subdomain; the dashboard is separate):

| Env var            | Purpose                         |
|--------------------|---------------------------------|
| `DASHBOARD_HOST`   | Dashboard UI                    |
| `API_HOST`         | Dashboard API (`api.*`)         |
| `SDK_HOST`         | Mobile SDK (`sdk.*`)            |
| `MCP_HOST`         | MCP OAuth/API (`mcp.*`)         |
| `GO_HOST`          | Short-link helper (`go.*`)      |
| `LINKS_PROD_HOST`  | Production links                |
| `LINKS_TEST_HOST`  | Test links                      |
| `PREVIEW_HOST`     | Link previews (`preview.*`)     |

## What runs

`proxy` (Caddy, TLS) · `postgres` · `redis` (AOF, no eviction) · `minio` (+ one-shot
bucket creation) · `backend-migrate` (one-shot migrate+seed) · `backend-web-1/2`
(Puma) · `backend-worker-1` (scheduler + events + batch) · `backend-worker-2`
(maintenance + device updates) · `dashboard` (Next.js).

`backend-worker-1` carries the **scheduler** (the cron that drives event processing) —
it is a singleton, **never scale it**.

## Email (optional)

Email is off by default. Invites use copyable links and the bootstrap admin needs no
email. Set `MAILER_DELIVERY_METHOD=smtp` and the `SMTP_*` vars only if you want
**password reset** or **data-export** emails.

## Upgrades

```bash
git submodule update --remote --merge        # pull latest backend + dashboard from GitHub
docker compose build
docker compose run --rm backend-migrate      # migrate BEFORE restarting web/workers
docker compose up -d
```

## Backups

Durable state lives in named volumes: `pg_data` (system of record — `pg_dump` it
off-box), `minio_data` (uploaded assets/exports — mirror the bucket), and `redis_data`
(AOF; only undrained events are at risk).

## Local testing without public DNS

Caddy's Let's Encrypt TLS needs public DNS. To try the stack on one machine, either
use real DNS, or replace the hostnames in `Caddyfile` with `http://localhost` blocks
and map the host ports.
