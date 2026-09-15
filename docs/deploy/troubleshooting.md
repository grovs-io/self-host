# Troubleshoot a self-hosted deployment

## Which containers should run?

`postgres`, `redis`, `clickhouse`, `web`, `worker-1`, `worker-2` and `dashboard`
should stay running. The standalone deployment also runs `proxy`. `migrate`
should exit successfully. An exit code other than 0 there blocks application
startup.

From the installation directory:

```bash
docker compose ps -a
docker compose logs --tail=100 migrate web worker-1 worker-2
docker compose logs --tail=100 postgres redis clickhouse
```

For cloud VMs, use `/opt/grovs` as root. In Coolify/Dokploy, use the corresponding
service logs. For a local trial, add
`-f docker-compose.yml -f docker-compose.local.yml` after `docker compose`.

## Images cannot be pulled

Check `GROVS_VERSION` and verify that both GHCR packages contain that release and
allow anonymous pulls. Public source repositories do not automatically make
their packages public. An image that was only built locally is not available to
new servers until the release workflow pushes it.

## Dashboard works, project links fail

Check all three pieces:

1. Wildcard DNS points to the correct server, including `*.test.<links-domain>`.
2. The reverse proxy routes the actual project hostname to `web:3000`.
3. Its certificate covers that hostname. `*.<links-domain>` does not cover
   `<project>.test.<links-domain>`; the test domain needs its own wildcard.

In the platform template, the dashboard's explicit router has higher priority
than the API/link router. Keep `GROVS_ROUTER_PREFIX` unique on the shared proxy.
The `GROVS_*_DOMAIN_PATTERN` values are generated from your link domains; update
them too if you change domains.

## Coolify/Dokploy reports a proxy or certificate error

Verify the external Docker network exists and the Traefik proxy is connected to
it. Check the entrypoint and certificate resolver names against the platform
environment file. This template uses Traefik v3 `HostRegexp` rules and requires
a DNS-01 resolver for wildcard certificates. Keep the standalone Caddy profile
off on these platforms.

## Login fails after a successful migration

The API and dashboard must share the same `OAUTH_CLIENT_UID` and
`OAUTH_CLIENT_SECRET`. Import the complete generated environment rather than
generating credentials separately for each service. Confirm the configured
`API_HOST` is reachable from the dashboard container.

## Analytics is temporarily unavailable

Wait for the first scheduled rollup, then inspect `worker-1` and ClickHouse logs.
Verify all three databases are healthy. Do not disable the shipped ClickHouse
flags to suppress an error: ClickHouse is the analytics/event store.

## How do I reset everything?

For a disposable local trial, see [local cleanup](local.md#stop-and-resume).
For a public installation, back up your data and secrets first. Restarting
containers preserves volumes; `docker compose down --volumes` deletes them.
