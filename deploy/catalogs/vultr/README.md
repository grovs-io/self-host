# Vultr Marketplace package

The Packer recipe builds Ubuntu 24.04 with Docker and public Grovs images. On a
customer's first boot, a cloud-init per-instance script reads Vultr application
variables and generates that installation's credentials. No image has been built
or deployed on Vultr yet; the package has local checks only.

## Maintainer: build and submit

Use the [official vendor tools](https://github.com/vultr/vultr-marketplace) to
create a vendor account and application. Add these required string variables:

| Variable name | Label | Example |
|---|---|---|
| `grovs_domain` | App domain, without a scheme or path | `grovs.example.com` |
| `grovs_admin_email` | First administrator email | `admin@example.com` |

The first-boot script reads `app-grovs_domain` and `app-grovs_admin_email` from the
[instance metadata service](https://docs.vultr.com/platform/marketplace/provisioning-scripts/create-provisioning-scripts).
No password is submitted as an application variable.

Local checks, from this directory:

```bash
packer init grovs.pkr.hcl
packer validate -var api_token=local-validation-only grovs.pkr.hcl
```

After paid validation is authorized, set `VULTR_API_KEY` privately and run
`packer build grovs.pkr.hcl`. This creates a billable instance and snapshot. The
recipe uses Ubuntu 24.04 x64, Frankfurt and a 4 vCPU / 8 GB builder. Review the
pinned official helper before building: `finalize-image.sh` calls its
`clean_system` function to remove builder identity, history and instance state.
Never execute image cleanup on an existing installation.

Attach the resulting image to the vendor application, then deploy through the
application flow with both variables. Complete the [fresh-install checks](../README.md),
including unique secrets on two installations and persistence after a reboot.
Submit the image, [listing copy](../../../docs/deploy/marketplaces.md), artwork and
documentation through the vendor console. Record the review ID and public URL.

## Customer: first setup

Select at least 4 vCPU, 8 GB RAM and 80 GB SSD. Enter your domain and admin email
in the deployment form, then configure DNS as shown in the
[Vultr guide](../../../docs/deploy/vultr.md). Allow ports 80 and 443 for HTTPS.
First boot starts Grovs automatically.

After connecting with your SSH key:

```bash
sudo cloud-init status --wait
sudo systemctl status grovs --no-pager
sudo cat /opt/grovs/.env
```

Keep the last command's output private. Sign in at
`https://dashboard.YOUR_APP_DOMAIN` using `BOOTSTRAP_ADMIN_EMAIL` and
`BOOTSTRAP_ADMIN_PASSWORD`. If setup failed, check `/var/log/cloud-init-output.log`,
`/opt/grovs/setup.log` and `sudo journalctl -u grovs`. Once missing inputs or DNS are
fixed, `sudo grovs-setup YOUR_APP_DOMAIN YOUR_ADMIN_EMAIL` retries setup while
preserving existing secrets.

Follow the [operations guide](../../../README.md) for backups and upgrades.
Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
