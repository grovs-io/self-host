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


def load_generator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("panels", ROOT / "scripts/generate-panel-catalogs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DokployTemplateTest(unittest.TestCase):
    """The Dokploy blueprint must follow the upstream catalog rules and stay self-consistent."""

    @classmethod
    def setUpClass(cls):
        import tomllib
        cls.generator = load_generator()
        cls.compose, toml_text, cls.meta = cls.generator.dokploy()
        cls.template = tomllib.loads(toml_text)
        cls.services = cls.compose["services"]

    def test_databases_are_private_and_persistent_and_only_web_and_dashboard_are_exposed(self):
        self.assertEqual(set(self.services), {"postgres", "redis", "clickhouse", "migrate",
                                              "web", "worker-1", "worker-2", "dashboard"})
        self.assertNotIn("networks", self.compose)
        for name, service in self.services.items():
            self.assertNotIn("ports", service, name)
            self.assertNotIn("networks", service, name)
            self.assertNotIn("container_name", service, name)
            self.assertIn(service["restart"], ("unless-stopped", "no"), name)
            self.assertEqual(service.get("expose"), [3000] if name in ("web", "dashboard") else None, name)
        for role, path in (("postgres", "/var/lib/postgresql/data"), ("redis", "/data"),
                           ("clickhouse", "/var/lib/clickhouse")):
            volume = self.services[role]["volumes"][0]
            self.assertTrue(volume.endswith(":" + path), volume)
            self.assertIn(volume.split(":")[0], self.compose["volumes"])
        for role in ("migrate", "web", "worker-1", "worker-2"):
            self.assertIn("storage:/app/storage", self.services[role]["volumes"], role)
        for image in (service["image"] for service in self.services.values()):
            self.assertRegex(image, r":\d+\.\d+", image)

    def test_web_starts_after_migrations_and_workers_after_web(self):
        self.assertEqual(self.services["web"]["depends_on"], {"migrate": {"condition": "service_completed_successfully"}})
        self.assertEqual(self.services["migrate"]["restart"], "no")
        for role in ("worker-1", "worker-2", "dashboard"):
            self.assertEqual(self.services[role]["depends_on"], {"web": {"condition": "service_healthy"}})
        self.assertNotIn("<<", str(self.compose))

    def test_domains_cover_every_fixed_host_and_point_at_existing_services(self):
        domains = {domain["host"]: domain for domain in self.template["config"]["domains"]}
        expected = {"dashboard.${main_domain}": "dashboard"}
        for prefix in ("api", "sdk", "mcp", "go", "preview", "links", "links.test"):
            expected[prefix + ".${main_domain}"] = "web"
        self.assertEqual({host: domain["serviceName"] for host, domain in domains.items()}, expected)
        for domain in domains.values():
            self.assertEqual(domain["port"], 3000)
            self.assertIn(domain["serviceName"], self.services)
        self.assertEqual(self.template["variables"]["main_domain"], "${domain}")

    def test_secrets_are_generated_per_installation_and_database_passwords_are_url_safe(self):
        env = dict(entry.split("=", 1) for entry in self.template["config"]["env"])
        variables = self.template["variables"]
        # Redis stays unauthenticated on the stack's private network, as in the standalone stack.
        for key in [key for key in self.generator.SECRETS if key != "REDIS_PASSWORD"]:
            match = re.fullmatch(r"\$\{(\w+)\}", env[key])
            self.assertIsNotNone(match, key)
            self.assertRegex(variables[match.group(1)], r"^\$\{(password|hash|base64):\d+\}$", key)
        for key in ("POSTGRES_PASSWORD", "CLICKHOUSE_PASSWORD"):
            self.assertRegex(variables[env[key][2:-1]], r"^\$\{(password|hash):\d+\}$", key)
        for value in env.values():
            for name in re.findall(r"\$\{(\w+)\}", value):
                self.assertIn(name, variables, value)

    def test_hosts_derive_from_four_env_values_and_compose_interpolation_is_satisfied(self):
        env = dict(entry.split("=", 1) for entry in self.template["config"]["env"])
        for key, value in {"SERVER_HOST": "${main_domain}", "DOMAIN_LIVE": "${main_domain}",
                           "DOMAIN_TEST": "test.${main_domain}", "SERVER_HOST_PROTOCOL": "http://",
                           "BOOTSTRAP_ADMIN_EMAIL": "admin@${main_domain}"}.items():
            self.assertEqual(env[key], value, key)
        backend = self.services["web"]["environment"]
        self.assertEqual(backend["API_HOST"], "api.${SERVER_HOST}")
        self.assertEqual(backend["LINKS_TEST_HOST"], "links.${DOMAIN_TEST}")
        self.assertEqual(backend["MCP_CONSENT_URL"], "${SERVER_HOST_PROTOCOL}dashboard.${SERVER_HOST}/mcp/authorize")
        self.assertEqual(self.services["dashboard"]["environment"]["API_URL"], "${SERVER_HOST_PROTOCOL}api.${SERVER_HOST}")
        self.assertEqual(backend["ACTIVE_STORAGE_SERVICE"], "local")
        for role in ("migrate", "worker-1", "worker-2"):
            self.assertEqual(self.services[role]["environment"], backend, role)
        referenced = set(re.findall(r"\$\{(\w+)\}", json.dumps(self.compose)))
        self.assertEqual(referenced - set(env), {"APP_NAME"})

    def test_web_routes_wildcard_project_links_without_manual_domains(self):
        labels = dict(label.split("=", 1) for label in self.services["web"]["labels"])
        rule = "HostRegexp(`^[a-z0-9-]+\\.${DOMAIN_LIVE}$$`) || HostRegexp(`^[a-z0-9-]+\\.${DOMAIN_TEST}$$`)"
        for router, entrypoint in (("${APP_NAME}-links", "web"), ("${APP_NAME}-links-secure", "websecure")):
            self.assertEqual(labels[f"traefik.http.routers.{router}.rule"], rule)
            self.assertEqual(labels[f"traefik.http.routers.{router}.entrypoints"], entrypoint)
            self.assertEqual(labels[f"traefik.http.routers.{router}.priority"], "1")
            self.assertEqual(labels[f"traefik.http.routers.{router}.service"], "${APP_NAME}-links")
        self.assertEqual(labels["traefik.http.services.${APP_NAME}-links.loadbalancer.server.port"], "3000")
        secure = "traefik.http.routers.${APP_NAME}-links-secure."
        self.assertEqual(labels[secure + "tls"], "true")
        self.assertEqual(labels[secure + "tls.certresolver"], "${GROVS_CERT_RESOLVER:-}")
        self.assertEqual(labels[secure + "tls.domains[0].main"], "${DOMAIN_LIVE}")
        self.assertEqual(labels[secure + "tls.domains[0].sans"], "*.${DOMAIN_LIVE}")
        self.assertEqual(labels[secure + "tls.domains[1].main"], "${DOMAIN_TEST}")
        self.assertEqual(labels[secure + "tls.domains[1].sans"], "*.${DOMAIN_TEST}")
        self.assertIn("GROVS_CERT_RESOLVER=", self.template["config"]["env"])
        for name, service in self.services.items():
            if name != "web":
                self.assertNotIn("labels", service, name)

    def test_meta_matches_pinned_release_and_logo(self):
        package = CATALOGS / "dokploy/grovs"
        self.assertEqual(self.meta["id"], "grovs")
        self.assertEqual(self.meta["version"], self.services["web"]["image"].split(":")[1])
        self.assertEqual(self.meta["version"], self.services["dashboard"]["image"].split(":")[1])
        self.assertTrue((package / self.meta["logo"]).exists())
        self.assertEqual(set(self.meta["links"]), {"github", "website", "docs"})
        self.assertEqual(self.meta["tags"], [tag.lower() for tag in self.meta["tags"]])

    def test_import_blob_is_the_base64_json_dokploy_expects(self):
        import base64
        package = CATALOGS / "dokploy/grovs"
        payload = json.loads(base64.b64decode((CATALOGS / "dokploy/import.base64").read_text().strip()))
        self.assertEqual(payload, {"compose": (package / "docker-compose.yml").read_text(),
                                   "config": (package / "template.toml").read_text()})

    @unittest.skipUnless(shutil.which("docker"), "Install Docker to validate the Compose file")
    def test_compose_file_loads_with_the_template_env(self):
        package = CATALOGS / "dokploy/grovs"
        with tempfile.TemporaryDirectory() as temp:
            values = ["APP_NAME=grovs-test"]
            for entry in self.template["config"]["env"]:
                key, value = entry.split("=", 1)
                values.append(f"{key}={re.sub(r'\$\{\w+\}', 'placeholder', value)}")
            (Path(temp) / ".env").write_text("\n".join(values) + "\n")
            result = subprocess.run(["docker", "compose", "--env-file", str(Path(temp) / ".env"),
                                     "-f", str(package / "docker-compose.yml"), "config", "--quiet"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr.strip(), "")
