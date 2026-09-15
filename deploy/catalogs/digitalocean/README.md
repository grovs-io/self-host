# DigitalOcean Marketplace package

The recipe prepares an Ubuntu 24.04 snapshot with Docker, public Grovs images and
a `grovs-setup` command. It does not initialize databases or create application
credentials on the image builder. It has local checks only; there is no published
DigitalOcean listing or tested snapshot yet.

## Maintainer: build and submit

1. Complete [DigitalOcean vendor onboarding](https://marketplace.digitalocean.com/vendors).
2. Review `grovs.pkr.hcl`, the shared image preparation scripts and the pinned
   [DigitalOcean cleanup/check scripts](https://github.com/digitalocean/marketplace-partners).
3. Run these **local checks** from this directory with Packer installed:

   ```bash
   packer init grovs.pkr.hcl
   packer validate -var api_token=local-validation-only grovs.pkr.hcl
   ```

4. When paid validation is authorized, set `DIGITALOCEAN_TOKEN` privately and run
   `packer build grovs.pkr.hcl`. This creates a Droplet and snapshot that incur
   provider charges. The recipe uses Frankfurt and a 4 vCPU / 8 GB builder.
5. Launch a fresh Droplet from the resulting snapshot. Test the customer steps
   below and the scenarios in [the package checklist](../README.md). Confirm
   separate instances receive different application credentials and SSH host keys.
6. Submit the tested snapshot, [listing copy](../../../docs/deploy/marketplaces.md),
   artwork and documentation through the vendor portal. Record the submission ID
   and approved listing URL in the tracker.

Do not run `prepare-image.sh` or `finalize-image.sh` on an existing server. The
cleanup script removes instance identity and history for a marketplace snapshot.

## Customer: first setup

Use at least 4 vCPU, 8 GB RAM and 80 GB SSD. Point your domain and wildcard DNS
records at the Droplet's public IP using the [DNS guide](../../../docs/deploy/digitalocean.md).
Allow HTTP/HTTPS; the image uses SSH for initial administration.

Connect using your SSH key, then run:

```bash
sudo grovs-setup grovs.example.com admin@example.com
sudo systemctl status grovs --no-pager
sudo cat /opt/grovs/.env
```

The last command displays private configuration. Keep it private; use
`BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` to sign in at
`https://dashboard.grovs.example.com`. The setup command generates credentials on
this Droplet and starts the stack. HTTPS certificates need working public DNS.

For startup failures, inspect `/opt/grovs/setup.log` and
`sudo journalctl -u grovs`. Follow the [operations guide](../../../README.md)
for backups and upgrades; preserve `/opt/grovs/.env` and Docker volumes.

Support: [Grovs Community issues](https://github.com/grovs-io/self-host/issues).
