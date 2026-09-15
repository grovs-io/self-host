#!/usr/bin/env python3
"""Build the public Railway marketplace configuration, without reading .env."""
import argparse
import importlib.util
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paas", ROOT / "scripts/generate-paas.py")
paas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paas)


def variable(value="", description="", optional=False):
    return {"defaultValue": value, "description": description, "isOptional": optional}


def reference(service, key):
    return "${{" + service + "." + key + "}}"


def secret():
    return variable('${{secret(64, "abcdef0123456789")}}', "Generated uniquely for this deployment.")


def template():
    config, cmds = paas.defaults(), paas.commands()
    services = {}

    def service(name, image, variables, mount=None, start=None, public=False, health=None):
        sid = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://grovs.io/railway/" + name))
        deploy = {"numReplicas": 1, "sleepApplication": False, "restartPolicyType": "ALWAYS"}
        if start:
            deploy["startCommand"] = start
        if health:
            deploy.update(healthcheckPath=health, healthcheckTimeout=600)
        if mount:
            deploy["requiredMountPath"] = mount
        icon = {"postgres": "https://devicons.railway.app/i/postgresql.svg",
                "redis": "https://devicons.railway.app/i/redis.svg",
                "clickhouse": "https://devicons.railway.app/i/clickhouse.svg"}.get(name, "https://docs.grovs.io/logo.svg")
        item = {"name": name, "icon": icon, "source": {"image": image}, "build": {}, "deploy": deploy,
                "variables": variables, "networking": {"serviceDomains": {"<hasDomain>:3000": {}}} if public else {},
                "volumeMounts": {sid: {"mountPath": mount}} if mount else {}}
        services[sid] = item
        return item

    service("postgres", "postgres:16-alpine", {
        "POSTGRES_USER": variable("grovs"), "POSTGRES_DB": variable("grovs_production"),
        "POSTGRES_PASSWORD": secret(), "PGDATA": variable("/var/lib/postgresql/data/pgdata")},
        mount="/var/lib/postgresql/data")
    service("redis", "redis:7-alpine", {"REDIS_PASSWORD": secret()}, mount="/data",
            start='sh -ec \'exec redis-server --appendonly yes --maxmemory-policy noeviction --requirepass "$REDIS_PASSWORD"\'')
    service("clickhouse", "clickhouse/clickhouse-server:25.3", {
        "CLICKHOUSE_DB": variable("grovs_production"), "CLICKHOUSE_USER": variable("grovs"),
        "CLICKHOUSE_PASSWORD": secret()}, mount="/var/lib/clickhouse")

    excluded = {"COMPOSE_PROJECT_NAME", "GROVS_VERSION", "ACME_EMAIL", "PREVIEW_BASE_URL",
                "MCP_CONSENT_URL", "S3_ASSET_PREFIX", "SMTP_DOMAIN", "MAILER_FROM"}
    env = {key: secret() if value == "change-me" else variable(value, optional=not value)
           for key, value in config.items() if key not in excluded and not key.endswith("_HOST")}
    for key, description in {
        "SERVER_HOST": "App base domain, for example grovs.example.com; no https:// or path.",
        "DOMAIN_LIVE": "Production links base domain, for example links.example.com.",
        "DOMAIN_TEST": "Test links base domain, for example test.links.example.com.",
        "BOOTSTRAP_ADMIN_EMAIL": "Email address for the first administrator.",
        "AWS_S3_KEY_ID": "Access key for your private S3-compatible bucket.",
        "AWS_S3_ACCESS_KEY": "Secret access key for your private bucket.",
        "AWS_S3_REGION": "Bucket region, for example eu-north-1.",
        "AWS_S3_BUCKET": "Private bucket name shared by API and workers.",
    }.items():
        env[key] = variable(description=description)
    for key in ("S3_ENDPOINT", "S3_FORCE_PATH_STYLE"):
        env[key] = variable(description="Optional override for S3-compatible storage.", optional=True)
    for key, value in {"RAILS_ENV": "production", "GROVS_SELF_HOSTED": "true", "GROVS_EE": "false",
                       "RAILS_LOG_TO_STDOUT": "true", "RAILS_SERVE_STATIC_FILES": "true",
                       "ACTIVE_STORAGE_SERVICE": "amazon", "CLICKHOUSE_DATABASE": "grovs_production",
                       "PORT": "3000", "SMTP_DOMAIN": reference("web", "SERVER_HOST"),
                       "MAILER_FROM": "Grovs <noreply@" + reference("web", "SERVER_HOST") + ">"}.items():
        env[key] = variable(value)
    for name in ("postgres", "redis", "clickhouse"):
        env[name.upper() + "_HOST"] = variable(reference(name, "RAILWAY_PRIVATE_DOMAIN"))
        env[name.upper() + "_PASSWORD"] = variable(reference(name, name.upper() + "_PASSWORD"))
    version = config["GROVS_VERSION"]
    backend = "ghcr.io/grovs-io/backend:" + version
    web = service("web", backend, env, start=cmds["web"].replace("tcp://0.0.0.0:", "tcp://[::]:"),
                  public=True, health="/up")
    web["deploy"]["preDeployCommand"] = [cmds["migrate"]]
    for role in ("worker-1", "worker-2"):
        worker_env = {key: variable(reference("web", key)) for key in env}
        worker_env.update(WEB_HOST=variable(reference("web", "RAILWAY_PRIVATE_DOMAIN")), WEB_PORT=variable("3000"))
        service(role, backend, worker_env, start=cmds[role])
    service("dashboard", "ghcr.io/grovs-io/dashboard:" + version, {
        "API_URL": variable("https://api." + reference("web", "SERVER_HOST")),
        "OAUTH_CLIENT_UID": variable(reference("web", "OAUTH_CLIENT_UID")),
        "OAUTH_CLIENT_SECRET": variable(reference("web", "OAUTH_CLIENT_SECRET")),
        "HOSTNAME": variable("::"), "PORT": variable("3000")}, public=True, health="/login")
    descriptions = {
        "PORT": "HTTP listening port. Keep at 3000 to match Railway networking.",
        "HOSTNAME": "Listen on IPv6 and IPv4 for Railway's private network.",
        "API_URL": "Public API URL on your custom domain.",
        "PGDATA": "PostgreSQL data directory inside the persistent volume.",
        "POSTGRES_DB": "Grovs PostgreSQL database name.",
        "POSTGRES_USER": "Grovs PostgreSQL database user.",
        "CLICKHOUSE_DB": "Grovs ClickHouse database name.",
        "CLICKHOUSE_USER": "Grovs ClickHouse database user.",
        "CLICKHOUSE_DATABASE": "Analytics database used by the application.",
        "WEB_PORT": "Private API health-check port for worker startup.",
        "RAILS_ENV": "Run Rails in production mode.",
        "GROVS_SELF_HOSTED": "Enable self-hosted configuration and bootstrap login.",
        "GROVS_EE": "Keep false for the Community edition.",
        "RAILS_LOG_TO_STDOUT": "Send Rails logs to Railway's log viewer.",
        "RAILS_SERVE_STATIC_FILES": "Serve the backend's bundled static assets.",
        "ACTIVE_STORAGE_SERVICE": "Use S3 storage shared by the API and workers.",
        "WEB_CONCURRENCY": "Number of Puma web processes.",
        "RAILS_MAX_THREADS": "Maximum threads per web process.",
        "RAILS_DB_POOL": "Database connections available per process.",
        "SIDEKIQ_EVENTS_CONCURRENCY": "Concurrent jobs in the event worker.",
        "POSTGRES_MAX_CONNECTIONS": "Connection budget setting from the Compose defaults; Railway PostgreSQL tuning is separate.",
        "MAILER_DELIVERY_METHOD": "Leave empty to disable email; configure SMTP to enable it.",
        "MAILER_FROM": "Sender address used for outgoing Grovs emails.",
        "SMTP_ADDRESS": "SMTP server hostname; only used when email is enabled.",
        "SMTP_PORT": "SMTP server port.",
        "SMTP_DOMAIN": "Domain sent in the SMTP greeting.",
        "SMTP_USERNAME": "SMTP authentication username, if required.",
        "SMTP_PASSWORD": "SMTP authentication password, if required.",
        "SMTP_AUTHENTICATION": "SMTP authentication mechanism.",
        "SMTP_ENABLE_STARTTLS_AUTO": "Use STARTTLS when supported by the SMTP server.",
        "SERVER_HOST_PROTOCOL": "Public backend URL protocol.",
        "REACT_HOST_PROTOCOL": "Public dashboard URL protocol.",
        "DEFAULT_LOGO_URL": "Default app icon on link landing pages.",
        "DEFAULT_SOCIAL_PREVIEW_URL": "Default image for shared links.",
        "DEFAULT_LINK_TITLE": "Default link landing-page title.",
        "DEFAULT_LINK_SUBTITLE": "Default link landing-page description.",
        "PUBLIC_GO_PROJECT_IDENTIFIER": "Identifier for the built-in public redirect project.",
        "PG_SHADOW_WRITES": "Mirror event writes to PostgreSQL; disabled for ClickHouse-primary storage.",
        "REVENUE_READS_FROM_LEDGER": "Read purchase revenue from the event ledger.",
        "CLICKHOUSE_PRIMARY": "Use ClickHouse as the primary event store.",
        "CLICKHOUSE_WRITE_ENABLED": "Write analytics events to ClickHouse.",
        "CLICKHOUSE_READ_ENABLED": "Read analytics events from ClickHouse.",
        "CLICKHOUSE_ANALYTICS_ROLLUPS_READ_ENABLED": "Read pre-aggregated ClickHouse analytics.",
        "CLICKHOUSE_ATTRIBUTION_READ_ENABLED": "Read attribution data from ClickHouse.",
        "CLICKHOUSE_LINK_DIMENSIONS_READ_ENABLED": "Read link dimensions from ClickHouse.",
        "CLICKHOUSE_ROLLUP_FAST_LANE": "Enable the fast path for analytics rollups.",
        "DASHBOARD_CACHE_TTL_SECONDS": "Dashboard result cache lifetime in seconds.",
    }
    for item in services.values():
        for key, entry in item["variables"].items():
            if entry["description"]:
                continue
            if entry["defaultValue"].startswith("${{"):
                entry["description"] = "Shared reference to " + entry["defaultValue"][3:-2] + "; keep in sync with its source."
            else:
                entry["description"] = descriptions[key]
    return {"services": services}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / "deploy/railway/template.json"
    output = json.dumps(template(), indent=2) + "\n"
    if args.check:
        if path.read_text() != output:
            raise SystemExit("Railway template is stale; run scripts/generate-railway-template.py")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
