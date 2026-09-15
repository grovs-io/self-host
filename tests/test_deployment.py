"""Deployment checks. Cloud commands are simulated; Compose only renders config."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]


class DeploymentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="grovs-deploy-test-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GROVS_", "COMPOSE_"))}
        self.env.update(GROVS_DOMAIN="example.com", GROVS_ADMIN_EMAIL="admin@example.com")

    def run_script(self, script, *args, env=None, input="", success=True):
        result = subprocess.run([str(ROOT / script), *map(str, args)],
                                env=env or self.env, input=input, text=True,
                                capture_output=True, cwd=self.directory)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def prepare(self, platform="coolify", **settings):
        self.env.update(settings)
        self.run_script("scripts/prepare-platform.sh", platform, self.directory)
        return self.read_env()

    def read_env(self):
        return dict(line.split("=", 1) for line in
                    (self.directory / ".env").read_text().splitlines()
                    if line and not line.startswith("#"))

    def test_setup_generates_and_preserves_private_configuration(self):
        self.env.update(GROVS_CONFIG_DIR=str(self.directory), GROVS_VERSION="2.3.1")
        self.run_script("scripts/setup.sh")
        values = self.read_env()
        self.assertEqual(values["GROVS_VERSION"], "2.3.1")
        self.assertEqual(values["API_HOST"], "api.example.com")
        self.assertEqual(values["DOMAIN_TEST"], "test.example.com")
        self.assertRegex(values["SECRET_KEY_BASE"], r"^[a-f0-9]{128}$")
        self.assertRegex(values["BOOTSTRAP_ADMIN_PASSWORD"], r"^[a-f0-9]{24}$")
        path = self.directory / ".env"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        original = path.read_bytes()
        self.env["GROVS_VERSION"] = "9.9.9"
        self.run_script("scripts/setup.sh")
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_version_does_not_leave_a_partial_env(self):
        self.env.update(GROVS_CONFIG_DIR=str(self.directory), GROVS_VERSION="latest")
        self.run_script("scripts/setup.sh", success=False)
        self.assertFalse((self.directory / ".env").exists())

    def test_local_trial_custom_ports(self):
        self.env.update(GROVS_CONFIG_DIR=str(self.directory), GROVS_DOMAIN="local",
                        GROVS_WEB_PORT="8080", GROVS_DASHBOARD_PORT="8082")
        self.run_script("scripts/setup.sh")
        values = self.read_env()
        self.assertEqual(values["API_HOST"], "api.lvh.me:8080")
        self.assertEqual(values["REACT_HOST"], "dashboard.lvh.me:8082")
        self.assertEqual(values["SERVER_HOST_PROTOCOL"], "http://")

    def test_platform_networks_domains_and_preservation(self):
        for platform, network, http, https in (
            ("coolify", "coolify", "http", "https"),
            ("dokploy", "dokploy-network", "web", "websecure"),
        ):
            with self.subTest(platform=platform):
                output = self.directory / platform
                self.env["GROVS_LINKS_DOMAIN"] = "acme.link"
                self.run_script("scripts/prepare-platform.sh", platform, output)
                text = (output / ".env").read_text()
                for entry in (f"GROVS_PROXY_NETWORK={network}",
                              f"GROVS_HTTP_ENTRYPOINT={http}",
                              f"GROVS_HTTPS_ENTRYPOINT={https}",
                              "GROVS_LINKS_DOMAIN_PATTERN=acme[.]link",
                              "GROVS_TEST_DOMAIN_PATTERN=test[.]acme[.]link"):
                    self.assertIn(entry, text)
                self.assertNotIn("COMPOSE_PROJECT_NAME=", text)
                self.run_script("scripts/prepare-platform.sh", platform, output)
                self.assertEqual((output / ".env").read_text(), text)

    def test_platform_rejects_local_and_malformed_domains(self):
        for domain in ("local", "lvh.me", "https://example.com", "example.com:80", "foo`bar.com"):
            with self.subTest(domain=domain):
                self.env["GROVS_DOMAIN"] = domain
                self.run_script("scripts/prepare-platform.sh", "coolify", self.directory, success=False)
                self.assertFalse((self.directory / ".env").exists())

    @unittest.skipUnless(shutil.which("docker"), "Docker Compose is required for rendering")
    def test_platform_compose_routing_dependencies_and_shared_secrets(self):
        self.prepare(GROVS_LINKS_DOMAIN="acme.link")
        result = subprocess.run([
            "docker", "compose", "--env-file", str(self.directory / ".env"),
            "-f", str(ROOT / "docker-compose.platform.yml"), "config", "--format", "json",
        ], text=True, capture_output=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        services = config["services"]
        self.assertEqual(set(services), {"postgres", "redis", "clickhouse", "migrate",
                                         "web", "dashboard", "worker-1", "worker-2"})
        for service in services.values():
            self.assertNotIn("ports", service)
            self.assertNotIn("env_file", service)
        web = services["web"]
        env = web["environment"]
        for key in ("OAUTH_CLIENT_UID", "OAUTH_CLIENT_SECRET"):
            self.assertEqual(env[key], services["dashboard"]["environment"][key])
        self.assertEqual(env["GROVS_EE"], "false")
        self.assertEqual(env["CLICKHOUSE_READ_ENABLED"], "true")
        self.assertEqual(web["depends_on"]["migrate"]["condition"], "service_completed_successfully")
        self.assertEqual(set(web["networks"]), {"default", "proxy"})
        self.assertEqual(set(services["postgres"]["networks"]), {"default"})
        self.assertEqual(config["networks"]["proxy"]["name"], "coolify")
        self.assertEqual(services["migrate"]["restart"], "no")
        self.assertIn("clickhouse:setup", services["migrate"]["command"][-1])
        labels = web["labels"]
        rule = next(v for k, v in labels.items() if k.endswith("-web.rule"))
        self.assertIn("Host(`api.example.com`)", rule)
        patterns = re.findall(r"HostRegexp\(`([^`]+)`\)", rule)
        self.assertEqual(len(patterns), 2)
        for hostname, expected in (("project.acme.link", True), ("project.test.acme.link", True),
                                    ("project.acmexlink", False), ("project.acme.link.evil.com", False)):
            self.assertEqual(any(re.fullmatch(p, hostname) for p in patterns), expected, hostname)
        cert_domains = {v for k, v in labels.items() if k.endswith(".main")}
        self.assertEqual(cert_domains, {"example.com", "acme.link", "test.acme.link"})
        self.assertIn("sidekiq_scheduler.yml", services["worker-1"]["command"][-1])

        # Render the canonical stack beside the temporary .env, never the real one.
        shutil.copy(ROOT / "docker-compose.yml", self.directory / "docker-compose.yml")
        base = subprocess.run([
            "docker", "compose", "--project-directory", str(self.directory),
            "--env-file", str(self.directory / ".env"),
            "-f", str(self.directory / "docker-compose.yml"),
            "--profile", "standalone", "config", "--format", "json",
        ], capture_output=True, text=True, env=self.env)
        self.assertEqual(base.returncode, 0, base.stderr)
        original = json.loads(base.stdout)["services"]
        for name, service in services.items():
            for key in ("image", "command", "depends_on", "volumes", "healthcheck", "restart"):
                self.assertEqual(service.get(key), original[name].get(key), f"{name}.{key}")

    def install_fake_gcloud(self):
        executable = self.directory / "gcloud"
        executable.write_text("""#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['FAKE_GCLOUD_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
if 'describe' in sys.argv:
    print('203.0.113.10')
for arg in sys.argv:
    if arg.startswith('--metadata-from-file='):
        source = arg.split('=', 2)[2]
        pathlib.Path(os.environ['FAKE_STARTUP']).write_text(pathlib.Path(source).read_text())
""")
        executable.chmod(0o755)
        self.env.update(PATH=f"{self.directory}:{self.env['PATH']}",
                        FAKE_GCLOUD_LOG=str(self.directory / "commands.jsonl"),
                        FAKE_STARTUP=str(self.directory / "startup.sh"))

    def test_gcp_commands_keep_project_scoped_and_disk_persistent(self):
        self.install_fake_gcloud()
        self.run_script("deploy/gcp/deploy.sh", "my-project", "europe-west1-b",
                        "example.com", "admin@example.com", "2.3.0", input="y\n")
        commands = [json.loads(line) for line in
                    (self.directory / "commands.jsonl").read_text().splitlines()]
        self.assertEqual(len(commands), 8)
        self.assertTrue(all(c[0] == "--project=my-project" for c in commands))
        create = commands[-1]
        for arg in ("--no-service-account", "--no-scopes", "--no-boot-disk-auto-delete",
                    "--address=203.0.113.10", "--metadata=enable-oslogin=TRUE"):
            self.assertIn(arg, create)
        startup = (self.directory / "startup.sh").read_text()
        self.assertIn("GROVS_DOMAIN=example.com", startup)
        self.assertIn("GROVS_VERSION=2.3.0", startup)
        self.assertIn("/etc/systemd/system/grovs.service", startup)
        self.assertNotIn("BOOTSTRAP_ADMIN_PASSWORD=", startup)

    def test_gcp_declining_creates_nothing(self):
        self.install_fake_gcloud()
        self.run_script("deploy/gcp/deploy.sh", "my-project", "europe-west1-b",
                        "example.com", "admin@example.com", input="n\n")
        self.assertFalse((self.directory / "commands.jsonl").exists())

    def test_aws_launch_url_encodes_template(self):
        template = "https://templates.s3.us-east-1.amazonaws.com/grovs/2.3.0/cloudformation.yaml"
        url = self.run_script("deploy/aws/launch-link.sh", "us-east-1", template).stdout.strip()
        query = parse_qs(urlparse(url).fragment.split("?", 1)[1])
        self.assertEqual(query["templateURL"], [template])
        self.assertEqual(query["stackName"], ["grovs-community"])
        self.run_script("deploy/aws/launch-link.sh", "us-east-1", "http://example.com/a", success=False)

    def test_generated_compose_is_current(self):
        self.run_script("scripts/generate-platform-compose.py", "--check")

    def test_shell_scripts_parse(self):
        for path in list((ROOT / "scripts").glob("*.sh")) + list((ROOT / "deploy").rglob("*.sh")):
            result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{path}: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
