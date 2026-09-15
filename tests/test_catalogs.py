"""Local catalog checks: no provider API calls or server provisioning."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "deploy/catalogs"


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((CATALOGS / "caprover/grovs.yml").read_text())
        self.services = {k.removeprefix("$$cap_appname-"): v
                         for k, v in self.config["services"].items()}

    def test_generated_packages_are_current(self):
        subprocess.run(["python3", str(ROOT / "scripts/generate-panel-catalogs.py"), "--check"], check=True)

    def test_caprover_credentials_resolve_to_shared_generated_fields(self):
        fields = {v["id"]: v for v in self.config["caproverOneClickApp"]["variables"]}
        for service in self.services.values():
            for value in service.get("environment", {}).values():
                for ref in re.findall(r"\$\$cap_[A-Z0-9_]+", value):
                    self.assertIn(ref, fields)
        web = self.services["web"]["environment"]
        for role in ("worker-1", "worker-2", "dashboard"):
            self.assertEqual(self.services[role]["environment"]["OAUTH_CLIENT_SECRET"], web["OAUTH_CLIENT_SECRET"])
        for key in ("SECRET_KEY_BASE", "OAUTH_CLIENT_SECRET", "ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY"):
            self.assertEqual(fields[web[key]]["defaultValue"], "$$cap_gen_random_hex(32)")
        for role in ("postgres", "clickhouse"):
            key = role.upper() + "_PASSWORD"
            self.assertEqual(self.services[role]["environment"][key], web[key])
        self.assertIn(web["REDIS_PASSWORD"], self.services["redis"]["command"])

    def test_databases_are_private_and_persistent(self):
        self.assertEqual(len(self.services), 7)
        for role, path in (("postgres", "/var/lib/postgresql/data"),
                           ("redis", "/data"), ("clickhouse", "/var/lib/clickhouse")):
            service = self.services[role]
            self.assertNotIn("ports", service)
            self.assertEqual(service["caproverExtra"]["notExposeAsWebApp"], "true")
            self.assertEqual(service["volumes"], [f"$$cap_appname-{role}-data:{path}"])

    def test_web_stops_on_each_failed_migration_and_starts_only_after_success(self):
        # Run the actual generated entry point with fake dependencies and executables.
        # This verifies bash failure propagation without starting Grovs or a database.
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            (work / "bin").mkdir()
            fake = work / "fake"
            fake.mkdir()
            scripts = {
                fake / "ruby": "#!/bin/sh\nexit 0\n",
                fake / "curl": "#!/bin/sh\nexit 0\n",
                fake / "bundle": '#!/bin/sh\necho puma >> "$CALL_LOG"\n',
                work / "bin/rails": '#!/bin/sh\necho "$1" >> "$CALL_LOG"\n[ "$1" != "$FAIL_STEP" ]\n',
            }
            for path, content in scripts.items():
                path.write_text(content)
                path.chmod(0o755)
            env = {**os.environ, **self.services["web"]["environment"],
                   "PATH": str(fake) + ":" + os.environ["PATH"], "CALL_LOG": str(work / "calls")}
            stages = ["db:prepare", "db:seed", "clickhouse:setup"]
            for index, stage in enumerate(stages + [""]):
                with self.subTest(failing_stage=stage or "none"):
                    (work / "calls").write_text("")
                    result = subprocess.run(self.services["web"]["command"], cwd=work,
                                            env={**env, "FAIL_STEP": stage}, capture_output=True, text=True)
                    calls = (work / "calls").read_text().splitlines()
                    if stage:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(calls, stages[:index + 1])
                    else:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(calls, stages + ["puma"])

    def test_shell_scripts_parse_and_image_cleanup_requires_explicit_build_mode(self):
        for path in CATALOGS.rglob("*.sh"):
            subprocess.run(["bash", "-n", str(path)], check=True)
        env = dict(os.environ)
        env.pop("GROVS_IMAGE_BUILD", None)
        # All three must refuse before executing any provisioning or cleanup commands.
        for name in ("shared/prepare-image.sh", "digitalocean/finalize-image.sh", "vultr/finalize-image.sh"):
            result = subprocess.run(["bash", str(CATALOGS / name)], env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0, name)

    def test_package_documentation_links_point_to_existing_files(self):
        for path in CATALOGS.rglob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" not in link and not link.startswith("#"):
                    self.assertTrue((path.parent / link.split("#", 1)[0]).exists(), (path, link))

    @unittest.skipUnless(shutil.which("ansible-playbook"), "Install ansible-core for input validation")
    def test_akamai_checks_inputs_without_provisioning(self):
        env = {**os.environ, "GROVS_DOMAIN": "grovs.example.com",
               "GROVS_ADMIN_EMAIL": "admin@example.com", "SUDO_USER_NAME": "grovsadmin",
               "PUBKEY": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFixture",
               "SSH_SOURCE_CIDR": "203.0.113.10/32"}
        app = CATALOGS / "akamai/apps/linode-marketplace-grovs"
        for override in ({}, {"SSH_SOURCE_CIDR": "999.0.0.1/32"},
                         {"SUDO_USER_NAME": "root"}, {"GROVS_DOMAIN": ""}):
            with self.subTest(override=override):
                result = subprocess.run(["ansible-playbook", "provision.yml"],
                                        cwd=app, env={**env, **override}, capture_output=True, text=True)
                self.assertNotIn("Unable to parse", result.stderr)
                if override:
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("All assertions passed", result.stdout)
