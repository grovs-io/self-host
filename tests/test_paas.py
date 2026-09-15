import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PaasTest(unittest.TestCase):
    def test_generated_files_current(self):
        subprocess.run(["python3", str(ROOT / "scripts/generate-paas.py"), "--check"], check=True)
        subprocess.run(["python3", str(ROOT / "scripts/generate-railway-template.py"), "--check"], check=True)

    def test_railway_template_references_resolve_without_cycles(self):
        config = json.loads((ROOT / "deploy/railway/template.json").read_text())
        services = {s["name"]: s for s in config["services"].values()}
        graph = {}
        for name, service in services.items():
            for key, entry in service["variables"].items():
                self.assertTrue(entry["description"], (name, key))
                targets = re.findall(r"\$\{\{([\w-]+)\.([\w_]+)\}\}", entry["defaultValue"])
                graph[name, key] = targets
                for target, variable in targets:
                    self.assertIn(target, services)
                    if variable != "RAILWAY_PRIVATE_DOMAIN":
                        self.assertIn(variable, services[target]["variables"])
        def visit(node, ancestors):
            self.assertNotIn(node, ancestors, "Circular Railway variable reference")
            for target in graph.get(node, []):
                visit(tuple(target), ancestors | {node})
        for node in graph:
            visit(node, set())

    def test_railway_template_credentials_have_one_generated_owner(self):
        config = json.loads((ROOT / "deploy/railway/template.json").read_text())
        services = {s["name"]: s for s in config["services"].values()}
        for name, service in services.items():
            for key, entry in service["variables"].items():
                if not any(word in key for word in ("PASSWORD", "SECRET", "ENCRYPTION", "API_KEY", "WEBHOOK_KEY", "OAUTH_CLIENT_UID")):
                    continue
                value = entry["defaultValue"]
                self.assertTrue(not value or value.startswith("${{"), (name, key))
        for role in ("worker-1", "worker-2", "dashboard"):
            env = services[role]["variables"]
            self.assertEqual(env["OAUTH_CLIENT_SECRET"]["defaultValue"], "${{web.OAUTH_CLIENT_SECRET}}")
        for name in ("postgres", "redis", "clickhouse"):
            key = name.upper() + "_PASSWORD"
            self.assertIn("secret(64", services[name]["variables"][key]["defaultValue"])
            self.assertEqual(services["web"]["variables"][key]["defaultValue"], "${{" + name + "." + key + "}}")

    def test_railway_template_keeps_datastores_private_and_persistent(self):
        services = {s["name"]: s for s in json.loads((ROOT / "deploy/railway/template.json").read_text())["services"].values()}
        for name, path in {"postgres": "/var/lib/postgresql/data", "redis": "/data", "clickhouse": "/var/lib/clickhouse"}.items():
            self.assertFalse(services[name]["networking"])
            self.assertEqual([v["mountPath"] for v in services[name]["volumeMounts"].values()], [path])
        for role in ("worker-1", "worker-2"):
            self.assertEqual(services[role]["deploy"]["numReplicas"], 1)
            self.assertFalse(services[role]["deploy"]["sleepApplication"])
            self.assertNotIn("preDeployCommand", services[role]["deploy"])
        self.assertIn("[::]", services["web"]["deploy"]["startCommand"])
        self.assertTrue(services["web"]["deploy"]["preDeployCommand"])

    def test_render_secrets_storage_and_migration_ownership(self):
        config = json.loads((ROOT / "render.yaml").read_text())
        services = {s["name"]: s for s in config["services"]}
        self.assertEqual(len(services), 6)
        web = services["grovs-web"]
        keys = [entry["key"] for entry in web["envVars"]]
        self.assertEqual(len(keys), len(set(keys)))
        env = {entry["key"]: entry for entry in web["envVars"]}
        self.assertEqual(env["ACTIVE_STORAGE_SERVICE"]["value"], "amazon")
        self.assertEqual(env["AWS_S3_BUCKET"]["sync"], False)
        for service in services.values():
            if service["name"] != "grovs-clickhouse":
                self.assertNotIn("disk", service)
            if service["name"] != "grovs-web":
                self.assertNotIn("preDeployCommand", service)
        self.assertEqual(services["grovs-clickhouse"]["type"], "pserv")
        self.assertEqual(services["grovs-clickhouse"]["disk"]["mountPath"], "/var/lib/clickhouse")
        self.assertEqual(services["grovs-redis"]["maxmemoryPolicy"], "noeviction")
        for name in ("grovs-worker-1", "grovs-worker-2", "grovs-dashboard"):
            role = services[name]
            oauth = next(e for e in role["envVars"] if e["key"] == "OAUTH_CLIENT_SECRET")
            self.assertEqual(oauth["fromService"], {"name": "grovs-web", "type": "web", "envVarKey": "OAUTH_CLIENT_SECRET"})
        self.assertEqual(services["grovs-worker-1"]["numInstances"], 1)

    def test_embedded_commands_parse(self):
        for command in json.loads((ROOT / "deploy/paas/commands.json").read_text()).values():
            args = shlex.split(command)
            self.assertEqual(args[:2], ["bash", "-ec"])
            result = subprocess.run(["bash", "-n", "-c", args[2]], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("ruby"), "Ruby required to verify URL encoding")
    def test_runtime_builds_domains_and_encodes_database_passwords(self):
        env = {"PATH": os.environ["PATH"], "SERVER_HOST": "grovs.example.com",
               "DOMAIN_LIVE": "links.example.com", "DOMAIN_TEST": "test.links.example.com",
               "AWS_S3_KEY_ID": "dummy", "AWS_S3_ACCESS_KEY": "dummy", "AWS_S3_REGION": "eu-west-1",
               "AWS_S3_BUCKET": "dummy", "POSTGRES_HOST": "postgres.internal", "REDIS_HOST": "redis.internal",
               "CLICKHOUSE_HOST": "clickhouse.internal", "POSTGRES_PASSWORD": "a+b/c=:@",
               "REDIS_PASSWORD": "a+b/c=:@", "CLICKHOUSE_PASSWORD": "a+b/c=:@"}
        script = (ROOT / "deploy/paas/backend-env.sh").read_text()
        script += '\nruby -rjson -e \'puts JSON.generate(ENV.to_h)\''
        result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["CLICKHOUSE_URL"], "http://grovs:a%2Bb%2Fc%3D%3A%40@clickhouse.internal:8123")
        self.assertEqual(output["DATABASE_URL"], "postgres://grovs:a%2Bb%2Fc%3D%3A%40@postgres.internal:5432/grovs_production")
        self.assertEqual(output["REACT_HOST"], "dashboard.grovs.example.com")
        self.assertEqual(output["LINKS_TEST_HOST"], "links.test.links.example.com")
        del env["AWS_S3_BUCKET"]
        result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AWS_S3_BUCKET", result.stderr)

    def test_railway_preparation_preserves_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {k: v for k, v in os.environ.items() if not k.startswith("GROVS_")}
            env.update(GROVS_DOMAIN="grovs.example.com", GROVS_ADMIN_EMAIL="admin@example.com")
            command = [str(ROOT / "scripts/prepare-railway.sh"), directory]
            subprocess.run(command, env=env, input="", capture_output=True, text=True, check=True)
            path = Path(directory) / ".env"
            first = path.read_text()
            self.assertIn("REDIS_PASSWORD=", first)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            subprocess.run(command, env=env, input="", capture_output=True, text=True, check=True)
            self.assertEqual(path.read_text(), first)
