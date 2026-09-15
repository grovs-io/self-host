"""Validate first-boot payloads without executing provisioning or contacting clouds."""
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cloud_init", ROOT / "scripts/generate-cloud-init.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CloudInitTest(unittest.TestCase):
    def generate(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "scripts/generate-cloud-init.py"),
                               "--domain", "grovs.example.com", "--email", "admin@example.com",
                               *extra], text=True, capture_output=True)

    def test_payload_installs_shared_bootstrap_with_private_file_permissions(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("#cloud-config\n"))
        config = json.loads(result.stdout.split("\n", 1)[1])
        entry, = config["write_files"]
        self.assertEqual(entry["permissions"], "0700")
        self.assertEqual(entry["owner"], "root:root")
        self.assertEqual(config["runcmd"], [["bash", entry["path"]]])
        self.assertIn((ROOT / "deploy/vm/bootstrap.sh").read_text(), entry["content"])
        syntax = subprocess.run(["bash", "-n"], input=entry["content"], text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        self.assertLess(len(result.stdout.encode()), 32768)

    def test_header_passes_requested_values_without_interpreting_shell(self):
        email = "admin'$(echo injected)@example.com"
        config = MODULE.cloud_config("grovs.example.com", email, "2.3.1", "some-ref")
        script = config["write_files"][0]["content"]
        # Execute only parameter exports, never the provisioning script itself.
        header = script.split((ROOT / "deploy/vm/bootstrap.sh").read_text())[0]
        result = subprocess.run(["bash"], input=header+'printf "%s" "$GROVS_ADMIN_EMAIL"',
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, email)

    def test_overrides_select_release_and_source(self):
        result = self.generate("--version", "2.4.0", "--stack-ref", "release-2.4")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout.split("\n", 1)[1])
        script = config["write_files"][0]["content"]
        self.assertIn("export GROVS_VERSION=2.4.0\n", script)
        self.assertIn("export GROVS_STACK_REF=release-2.4\n", script)

    def test_invalid_inputs_emit_no_partial_payload(self):
        for key, value in [("--domain", "local"), ("--domain", "api.lvh.me"),
                           ("--domain", "https://example.com"), ("--domain", "a;echo bad.com"),
                           ("--email", "admin@example.com\nINJECT=1"),
                           ("--version", "latest"), ("--stack-ref", "x$(echo injected)")]:
            with self.subTest(key=key, value=value):
                result = self.generate(key, value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


class AzureTemplateTest(unittest.TestCase):
    def setUp(self):
        self.template = json.loads((ROOT / "deploy/azure/azuredeploy.json").read_text())
        self.resources = {r["type"]: r for r in self.template["resources"]}

    def test_network_exposes_only_web_and_operator_ssh(self):
        rules = self.resources["Microsoft.Network/networkSecurityGroups"]["properties"]["securityRules"]
        self.assertEqual(len(rules), 2)
        web, ssh = [r["properties"] for r in rules]
        self.assertEqual(web["destinationPortRanges"], ["80", "443"])
        self.assertEqual(ssh["destinationPortRange"], "22")
        self.assertEqual(ssh["sourceAddressPrefix"], "[parameters('sshSourceCidr')]")
        self.assertNotIn("defaultValue", self.template["parameters"]["sshSourceCidr"])
        subnet = self.resources["Microsoft.Network/virtualNetworks"]["properties"]["subnets"][0]
        self.assertIn("networkSecurityGroups", subnet["properties"]["networkSecurityGroup"]["id"])

    def test_vm_requires_ssh_key_and_retains_disk_on_vm_deletion(self):
        vm = self.resources["Microsoft.Compute/virtualMachines"]["properties"]
        linux = vm["osProfile"]["linuxConfiguration"]
        self.assertTrue(linux["disablePasswordAuthentication"])
        self.assertEqual(linux["ssh"]["publicKeys"][0]["keyData"], "[parameters('sshPublicKey')]")
        self.assertEqual(vm["storageProfile"]["osDisk"]["deleteOption"], "Detach")
        self.assertEqual(vm["storageProfile"]["imageReference"]["offer"], "ubuntu-24_04-lts")
        self.assertEqual(set(self.template["outputs"]), {"ipAddress", "dashboard", "vmName", "sshCommand"})

    def test_bootstrap_parameters_are_substituted_and_safely_encoded(self):
        variables = self.template["variables"]
        expression = variables["startup"]
        header = variables["startupTemplate"]
        for marker, name, value in [("__DOMAIN__", "appDomain", "grovs.example.com"),
                                    ("__EMAIL__", "adminEmail", "admin'$(echo injected)@example.com"),
                                    ("__VERSION__", "grovsVersion", "2.3.1"),
                                    ("__REF__", "stackRef", "some-ref")]:
            self.assertIn(f"'{marker}', base64(parameters('{name}'))", expression)
            header = header.replace(marker, base64.b64encode(value.encode()).decode())
        # Run just the parameter header to verify shell quoting, not the installer.
        result = subprocess.run(["bash"], input=header+'printf "%s" "$GROVS_ADMIN_EMAIL"',
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "admin'$(echo injected)@example.com")
        bootstrap = (ROOT / "deploy/vm/bootstrap.sh").read_text()
        self.assertIn(bootstrap, variables.values())
        vm = self.resources["Microsoft.Compute/virtualMachines"]["properties"]
        self.assertEqual(vm["osProfile"]["customData"], "[base64(variables('startup'))]")
