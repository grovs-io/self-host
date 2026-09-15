# Akamai / Linode Marketplace package

This package contains a StackScript entry point and an Ansible application for
Ubuntu 24.04. It creates a key-authenticated sudo operator, configures the host
firewall and starts the Grovs Compose stack with per-installation credentials.
Local syntax and input checks are available; no Linode was provisioned and no
upstream submission has been made.

## Package layout

- `deployment_scripts/linode-marketplace-grovs/grovs-deploy.sh`: StackScript UDFs
  and an isolated Ansible virtual environment.
- `apps/linode-marketplace-grovs/`: input validation, installation roles and
  [customer documentation](apps/linode-marketplace-grovs/DOCUMENTATION.md).
- `../shared/assets/`: Grovs black and white SVG marks for the provider's artwork.

## Local checks

With `ansible-core==2.18.4` installed, run from the application directory:

```bash
ansible-playbook --syntax-check provision.yml
ansible-playbook --syntax-check site.yml
```

`provision.yml` only validates required inputs. `site.yml` modifies the target
machine and must run only on a new Ubuntu server. Never run it on a workstation.

## Before an upstream submission

Follow the [contribution guide](https://github.com/akamai-compute-marketplace/marketplace-apps/blob/main/docs/CONTRIBUTING.md).
Copy the application and deployment script into the matching upstream folders.
Pin `GROVS_CATALOG_REF` to a published, reviewed commit containing this package
before deploying the StackScript. The application independently pins the shared
Grovs bootstrap and verifies its SHA-256 checksum.

When cloud testing is authorized, deploy a new Linode using the StackScript and
the inputs documented below. Verify SSH access as the new user, firewall rules,
unique credentials, all [application checks](../README.md) and reboot persistence.
Capture login and populated-dashboard screenshots using demo data. Include the
100–125 word description and support links from the
[listing copy](../../../docs/deploy/marketplaces.md#reusable-listing-copy), SVG
artwork and the completed customer documentation in the submission.

This package generates passwords on the instance instead of receiving them as
StackScript fields. Ansible marks secret-bearing tasks `no_log` and writes
credentials to a private file. Explain that design in the upstream review and
incorporate any provider-required changes before claiming compliance.

Record the PR and accepted listing URL in the submission tracker. Provider review
and actual installation tests remain separate from the local syntax checks.
