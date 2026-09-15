import { readFileSync } from "node:fs";
import { parseEnv } from "node:util";
import { defineRailway, image, project, service, volume } from "railway/iac";
import type { VariableValue } from "railway/iac";

// Secrets stay in the operator's private file; never generate new values during plan/apply.
const configPath = process.env.GROVS_CONFIG_FILE;
if (!configPath) throw new Error("Set GROVS_CONFIG_FILE to the private .env from prepare-railway.sh");
const config = parseEnv(readFileSync(configPath, "utf8"));
function required(key: string): string {
  const value = config[key];
  if (!value || ["change-me", "set-me"].includes(value)) throw new Error(`Set ${key} in GROVS_CONFIG_FILE`);
  return value;
}
for (const key of ["SERVER_HOST", "DOMAIN_LIVE", "DOMAIN_TEST"]) {
  const host = required(key);
  if (!/^[a-z0-9][a-z0-9.-]*\.[a-z0-9-]+$/.test(host) || host.endsWith("lvh.me")) {
    throw new Error(`${key} must be a public hostname without a scheme, path or port`);
  }
}
for (const key of ["AWS_S3_KEY_ID", "AWS_S3_ACCESS_KEY", "AWS_S3_REGION", "AWS_S3_BUCKET",
  "SECRET_KEY_BASE", "ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY", "ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY",
  "ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT", "OAUTH_CLIENT_UID", "OAUTH_CLIENT_SECRET",
  "BOOTSTRAP_ADMIN_PASSWORD", "POSTGRES_PASSWORD", "CLICKHOUSE_PASSWORD", "REDIS_PASSWORD"]) required(key);
const version = required("GROVS_VERSION");
if (!/^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$/.test(version)) throw new Error("Select a published GROVS_VERSION");
const commands: Record<string, string> = JSON.parse(readFileSync(new URL("../deploy/paas/commands.json", import.meta.url), "utf8"));
const source = (url: string) => image(url, { autoUpdates: { type: "disabled" } });
const alwaysRunning = { sleepApplication: false, restartPolicyType: "ALWAYS" as const };

export default defineRailway(() => {
  const pgData = volume("postgres-data", { sizeMB: 20480 });
  const redisData = volume("redis-data", { sizeMB: 5120 });
  const chData = volume("clickhouse-data", { sizeMB: 51200 });
  const postgres = service("postgres", {
    source: source("postgres:16-alpine"), replicas: 1, deploy: alwaysRunning,
    env: { POSTGRES_USER: "grovs", POSTGRES_DB: "grovs_production", POSTGRES_PASSWORD: required("POSTGRES_PASSWORD"),
      PGDATA: "/var/lib/postgresql/data/pgdata" },
    volumeMounts: { "/var/lib/postgresql/data": pgData },
  });
  const redis = service("redis", {
    source: source("redis:7-alpine"), replicas: 1, deploy: alwaysRunning,
    env: { REDIS_PASSWORD: required("REDIS_PASSWORD") },
    start: 'sh -ec \'exec redis-server --appendonly yes --maxmemory-policy noeviction --requirepass "$REDIS_PASSWORD"\'',
    volumeMounts: { "/data": redisData },
  });
  const clickhouse = service("clickhouse", {
    source: source("clickhouse/clickhouse-server:25.3"), replicas: 1, deploy: alwaysRunning,
    env: { CLICKHOUSE_DB: "grovs_production", CLICKHOUSE_USER: "grovs", CLICKHOUSE_PASSWORD: required("CLICKHOUSE_PASSWORD") },
    volumeMounts: { "/var/lib/clickhouse": chData },
  });
  const backendEnv: Record<string, string | VariableValue> = { ...config,
    RAILS_ENV: "production", GROVS_SELF_HOSTED: "true", GROVS_EE: "false",
    RAILS_LOG_TO_STDOUT: "true", RAILS_SERVE_STATIC_FILES: "true", ACTIVE_STORAGE_SERVICE: "amazon",
    POSTGRES_HOST: postgres.env.RAILWAY_PRIVATE_DOMAIN,
    REDIS_HOST: redis.env.RAILWAY_PRIVATE_DOMAIN,
    CLICKHOUSE_HOST: clickhouse.env.RAILWAY_PRIVATE_DOMAIN, CLICKHOUSE_DATABASE: "grovs_production", PORT: "3000",
  };
  // Discard standalone connection overrides; use this project's private network.
  for (const key of ["DATABASE_URL", "REDIS_URL", "CLICKHOUSE_URL"]) delete backendEnv[key];
  const web = service("web", {
    source: source(`ghcr.io/grovs-io/backend:${version}`), replicas: 1, deploy: alwaysRunning,
    env: backendEnv, start: commands.web.replace("tcp://0.0.0.0:", "tcp://[::]:"),
    preDeploy: commands.migrate, healthcheck: "/up", healthcheckTimeout: 600,
    domains: ["api", "sdk", "mcp", "go", "preview"].map(prefix => ({ domain: `${prefix}.${config.SERVER_HOST}`, port: 3000 }))
      .concat([config.DOMAIN_LIVE, config.DOMAIN_TEST].map(domain => ({ domain: `*.${domain}`, port: 3000 }))),
  });
  const workers = ["worker-1", "worker-2"].map(role => service(role, {
    source: source(`ghcr.io/grovs-io/backend:${version}`), replicas: 1, deploy: alwaysRunning,
    env: { ...backendEnv, WEB_HOST: web.env.RAILWAY_PRIVATE_DOMAIN, WEB_PORT: "3000" },
    start: commands[role],
  }));
  const dashboard = service("dashboard", {
    source: source(`ghcr.io/grovs-io/dashboard:${version}`), replicas: 1, deploy: alwaysRunning,
    env: { API_URL: `https://api.${config.SERVER_HOST}`, OAUTH_CLIENT_UID: required("OAUTH_CLIENT_UID"),
      OAUTH_CLIENT_SECRET: required("OAUTH_CLIENT_SECRET"), HOSTNAME: "::", PORT: "3000" },
    healthcheck: "/login", domains: [{ domain: `dashboard.${config.SERVER_HOST}`, port: 3000 }],
  });
  return project("grovs-community", { resources: [postgres, redis, clickhouse, web, ...workers, dashboard, pgData, redisData, chData] });
});
