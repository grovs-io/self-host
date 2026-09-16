# Marketplace submission packages

These are maintainer packages for Grovs Community 2.3.1. They are not published
catalog listings. Local validation does not establish that a deployment works on
the provider. No paid servers were created for this work.

| Target | Package | Remaining before submission |
|---|---|---|
| DigitalOcean | [Packer image recipe](digitalocean/README.md), per-customer setup, image cleanup | Vendor account, build and test a clean snapshot, portal submission |
| Vultr | [Packer image recipe](vultr/README.md), application variables, first boot, image cleanup | Vendor account and variables, build and test an image, portal submission |
| Akamai / Linode | [StackScript and Ansible](akamai/README.md), SSH operator, firewall, credentials | Fresh Linode test, real screenshots, upstream review |
| Easypanel | [Native template](easypanel/README.md), generated secrets, database volumes | Import into an Easypanel instance, verify wildcard TLS, capture a populated dashboard, upstream PR |
| CapRover | [One Click App](caprover/README.md), generated secrets, database volumes | Deploy on a CapRover instance, verify wildcard TLS, upstream PR |
| Dokploy | [Catalog blueprint](dokploy/README.md), Base64 import blob, generated secrets, database volumes | Deploy on a Dokploy instance, verify wildcard TLS, upstream PR |

## Local checks

From the repository root:

```bash
python3 scripts/generate-panel-catalogs.py --check
python3 -m unittest discover -s tests
```

The provider directories describe additional upstream schema, Packer and Ansible
checks. `packer validate` checks the recipe; `packer build` creates billable cloud
resources and is deliberately not part of the local checks.

Before submitting, record a fresh installation with migrations, HTTPS, login,
project creation, live/test links, SDK event ingestion, uploads, reboot and
backup/restore. Record the source commit and image versions. Screenshots must use
demo data and exclude credentials. See the [submission tracker](../../docs/deploy/marketplaces.md).

## Artwork and listing copy

`shared/assets/` contains Grovs's existing black and white square SVG marks. The
panel directories contain the same brand's required logo format. No screenshot
is supplied in place of a real deployment. Reusable descriptions and support
links are in the [submission tracker](../../docs/deploy/marketplaces.md#reusable-listing-copy).

## Updating packages

Regenerate panel files with `python3 scripts/generate-panel-catalogs.py`. Inputs
come from `.env.example`; never copy a real `.env` into a template or image.
Update VM recipe image versions, stack commit and bootstrap checksum together.
For image catalogs, build from fresh Ubuntu 24.04 and generate credentials only
on the customer's VM. Do not snapshot an initialized installation.
