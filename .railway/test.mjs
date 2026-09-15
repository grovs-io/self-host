// Evaluate the actual Railway SDK definition with disposable inputs; no API calls.
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRailwayContext, project } from "railway/iac";

const dir = mkdtempSync(join(tmpdir(), "grovs-railway-"));
const input = {
  SERVER_HOST: "grovs.example.com", DOMAIN_LIVE: "links.example.com", DOMAIN_TEST: "test.links.example.com",
  GROVS_VERSION: "2.3.0", AWS_S3_KEY_ID: "dummy", AWS_S3_ACCESS_KEY: "dummy",
  AWS_S3_REGION: "eu-west-1", AWS_S3_BUCKET: "dummy", SECRET_KEY_BASE: "dummy",
  ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY: "dummy", ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY: "dummy",
  ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT: "dummy", OAUTH_CLIENT_UID: "shared-uid", OAUTH_CLIENT_SECRET: "shared-secret",
  BOOTSTRAP_ADMIN_PASSWORD: "dummy", POSTGRES_PASSWORD: "dummy", CLICKHOUSE_PASSWORD: "dummy", REDIS_PASSWORD: "dummy",
};
try {
  const path = join(dir, ".env");
  writeFileSync(path, Object.entries(input).map(([k, v]) => `${k}=${v}`).join("\n"), { mode: 0o600 });
  process.env.GROVS_CONFIG_FILE = path;
  const { default: definition } = await import("./railway.ts");
  const result = await definition(createRailwayContext({ environment: "production", command: "plan" }), project);
  const resources = Object.fromEntries(result.resources.map(r => [r.name, r]));
  assert.equal(result.resources.length, 10);
  for (const role of ["postgres", "redis", "clickhouse"]) {
    assert.equal(resources[role].networking, undefined);
    assert.equal(Object.keys(resources[role].volumeAttachments).length, 1);
  }
  const web = resources.web;
  assert.equal(web.variables.POSTGRES_HOST.type, "reference");
  assert.equal(web.variables.POSTGRES_HOST.resource, "service.postgres");
  assert.equal(web.variables.REDIS_HOST.resource, "service.redis");
  assert.equal(web.variables.CLICKHOUSE_HOST.resource, "service.clickhouse");
  assert.ok(web.deploy.preDeployCommand[0].includes("clickhouse:setup"));
  assert.equal(web.variables.ACTIVE_STORAGE_SERVICE.value, "amazon");
  assert.equal(resources["worker-1"].deploy.numReplicas, 1);
  assert.equal(resources["worker-1"].deploy.sleepApplication, false);
  assert.equal(resources["worker-1"].variables.WEB_HOST.resource, "service.web");
  assert.deepEqual(resources.dashboard.variables.OAUTH_CLIENT_SECRET, web.variables.OAUTH_CLIENT_SECRET);
  assert.ok(web.networking.customDomains["*.links.example.com"]);
  assert.ok(web.networking.customDomains["*.test.links.example.com"]);
  assert.ok(!JSON.stringify(result).includes("[object Object]"));
  delete input.AWS_S3_BUCKET;
  writeFileSync(path, Object.entries(input).map(([k, v]) => `${k}=${v}`).join("\n"));
  await assert.rejects(import("./railway.ts?missing-bucket"), /AWS_S3_BUCKET/);
  console.log("Railway SDK evaluation and missing-input checks passed.");
} finally {
  rmSync(dir, { recursive: true, force: true });
}
