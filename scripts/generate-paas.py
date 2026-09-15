#!/usr/bin/env python3
"""Generate Render Blueprint and shared PaaS commands from the checked-in defaults."""
import argparse
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]


def defaults():
    result = {}
    for line in (ROOT / ".env.example").read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value[1:-1] if value.startswith('"') and value.endswith('"') else value
    return result


def commands():
    setup = (ROOT / "deploy/paas/backend-env.sh").read_text()
    def command(body):
        return "bash -ec " + shlex.quote(setup + "\n" + body)
    migrate = command('wait_for_http "http://$CLICKHOUSE_HOST:8123/ping"\n'
                      'bin/rails db:prepare && bin/rails db:seed && bin/rails clickhouse:setup')
    result = {"migrate": migrate,
              "web": command('exec bundle exec puma -b "tcp://0.0.0.0:${PORT:-3000}"')}
    groups = {"worker-1": ["scheduler", "worker", "batch"],
              "worker-2": ["maintenance", "device_updates"]}
    for role, queues in groups.items():
        body = 'wait_for_http "http://$WEB_HOST:${WEB_PORT:-3000}/up"\n'
        # Stop sibling processes when any worker exits; propagate termination.
        body += "pids=()\ntrap 'kill \"${pids[@]}\" 2>/dev/null || true' EXIT\ntrap 'exit 143' TERM INT\n"
        for queue in queues:
            body += f"bundle exec sidekiq -C config/sidekiq_{queue}.yml &\npids+=($!)\n"
        body += "wait -n\n"
        result[role] = command(body)
    return result


def render_blueprint(config, cmds):
    def value(key, val):
        return {"key": key, "value": val}
    def ref(key, name="grovs-web", kind="web", prop=None):
        return {"key": key, "fromService": {"name": name, "type": kind,
                **({"property": prop} if prop else {"envVarKey": key})}}
    # Hostnames are derived at runtime because Render does not interpolate values.
    excluded = {"COMPOSE_PROJECT_NAME", "GROVS_VERSION", "POSTGRES_PASSWORD", "CLICKHOUSE_PASSWORD",
                "ACME_EMAIL", "SERVER_HOST_PROTOCOL", "REACT_HOST_PROTOCOL", "REACT_HOST",
                "PREVIEW_BASE_URL", "MCP_CONSENT_URL", "S3_ASSET_PREFIX", "DOMAIN_LIVE", "DOMAIN_TEST",
                "SERVER_HOST", "SMTP_DOMAIN", "BOOTSTRAP_ADMIN_EMAIL", "MAILER_FROM"}
    env = []
    for key, val in config.items():
        if key in excluded or key.endswith("_HOST") or key.startswith("POSTGRES_"):
            continue
        env.append({"key": key, "generateValue": True} if val == "change-me" else value(key, val))
    env = [entry for entry in env if entry["key"] != "ACTIVE_STORAGE_SERVICE"]
    for key in ("SERVER_HOST", "DOMAIN_LIVE", "DOMAIN_TEST", "BOOTSTRAP_ADMIN_EMAIL",
                "AWS_S3_KEY_ID", "AWS_S3_ACCESS_KEY", "AWS_S3_REGION", "AWS_S3_BUCKET"):
        env.append({"key": key, "sync": False})
    for key, val in {"ACTIVE_STORAGE_SERVICE": "amazon", "GROVS_EE": "false",
                     "GROVS_SELF_HOSTED": "true", "RAILS_ENV": "production",
                     "RAILS_LOG_TO_STDOUT": "true", "RAILS_SERVE_STATIC_FILES": "true",
                     "CLICKHOUSE_DATABASE": "grovs_production", "PORT": "3000"}.items():
        env.append(value(key, val))
    env += [{"key": "DATABASE_URL", "fromDatabase": {"name": "grovs-postgres", "property": "connectionString"}},
            ref("REDIS_URL", "grovs-redis", "keyvalue", "connectionString"),
            ref("CLICKHOUSE_HOST", "grovs-clickhouse", "pserv", "host"),
            ref("CLICKHOUSE_PASSWORD", "grovs-clickhouse", "pserv")]
    backend_image = "ghcr.io/grovs-io/backend:" + config["GROVS_VERSION"]
    services = [{"name": "grovs-clickhouse", "type": "pserv", "runtime": "image",
                 "image": {"url": "clickhouse/clickhouse-server:25.3"}, "plan": "2c-4g",
                 "region": "frankfurt", "autoDeployTrigger": "off",
                 "disk": {"name": "clickhouse-data", "mountPath": "/var/lib/clickhouse", "sizeGB": 50},
                 "envVars": [value("CLICKHOUSE_DB", "grovs_production"), value("CLICKHOUSE_USER", "grovs"),
                             {"key": "CLICKHOUSE_PASSWORD", "generateValue": True}]},
                {"name": "grovs-redis", "type": "keyvalue", "plan": "1g", "region": "frankfurt",
                 "ipAllowList": [], "maxmemoryPolicy": "noeviction"}]
    for role in ("web", "worker-1", "worker-2"):
        role_env = env if role == "web" else [ref(entry["key"]) for entry in env]
        if role != "web":
            role_env = role_env + [ref("WEB_HOST", prop="host"), value("WEB_PORT", "3000")]
        item = {"name": "grovs-" + role, "type": "web" if role == "web" else "worker",
                "runtime": "image", "image": {"url": backend_image}, "plan": "1c-2g",
                "region": "frankfurt", "numInstances": 1, "autoDeployTrigger": "off",
                "dockerCommand": cmds[role], "envVars": role_env}
        if role == "web":
            item.update(healthCheckPath="/up", preDeployCommand=cmds["migrate"])
        services.append(item)
    services.append({"name": "grovs-dashboard", "type": "web", "runtime": "image",
                     "image": {"url": "ghcr.io/grovs-io/dashboard:" + config["GROVS_VERSION"]},
                     "plan": "1c-2g", "region": "frankfurt", "autoDeployTrigger": "off",
                     "healthCheckPath": "/login", "envVars": [
                         {"key": "API_URL", "sync": False}, ref("OAUTH_CLIENT_UID"), ref("OAUTH_CLIENT_SECRET"),
                         value("HOSTNAME", "0.0.0.0"), value("PORT", "3000")]})
    return {"services": services, "databases": [{"name": "grovs-postgres", "plan": "1c-2g",
             "region": "frankfurt", "postgresMajorVersion": "16", "diskSizeGB": 20,
             "databaseName": "grovs_production", "user": "grovs", "ipAllowList": []}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cmds = commands()
    outputs = {ROOT / "render.yaml": render_blueprint(defaults(), cmds),
               ROOT / "deploy/paas/commands.json": cmds}
    for path, content in outputs.items():
        text = json.dumps(content, indent=2) + "\n"  # JSON is valid YAML 1.2.
        if args.check:
            if not path.exists() or path.read_text() != text:
                raise SystemExit(f"{path.name} is stale; run scripts/generate-paas.py")
        else:
            path.write_text(text)


if __name__ == "__main__":
    main()
