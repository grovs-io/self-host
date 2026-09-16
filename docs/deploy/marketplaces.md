# Marketplace distribution for Grovs Community

Maintainer submission plan, checked 15 September 2026. Deployment guides and
buttons are available independently of official catalog approval. A catalog can
provide product discovery and a link to Grovs; acceptance, indexing and search
ranking benefits are controlled by the provider.

## Submission queue

| Priority | Platform | Submission route | Available now | Work before an official listing |
|---|---|---|---|---|
| 1 | DigitalOcean | [Become a vendor](https://marketplace.digitalocean.com/vendors) | [Packer recipe, image cleanup and customer setup](../../deploy/catalogs/digitalocean/README.md) | Vendor onboarding, build sanitized snapshot, live deployment test and review |
| In review | Vultr | [Vendor tools and application process](https://github.com/vultr/vultr-marketplace) | Vendor application submitted; [Packer recipe, application variables and first boot](../../deploy/catalogs/vultr/README.md) prepared | Confirm Community scope, sizing and delivery approach; complete onboarding, image build, live test and listing approval |
| 1 | Akamai / Linode | [Marketplace contribution guide](https://github.com/akamai-compute-marketplace/marketplace-apps/blob/main/docs/CONTRIBUTING.md) | [StackScript, Ansible, SSH operator and firewall](../../deploy/catalogs/akamai/README.md) | Live test, screenshots and upstream PR |
| 1 | Easypanel | [Template repository](https://github.com/easypanel-io/templates) | [Native template, logo and schema checks](../../deploy/catalogs/easypanel/README.md) | Live import, wildcard HTTPS verification, populated-dashboard screenshot and upstream PR |
| 1 | CapRover | [One Click Apps](https://github.com/caprover/one-click-apps) | [Template, logo and upstream validation](../../deploy/catalogs/caprover/README.md) | Live deployment, wildcard HTTPS verification and upstream PR |
| 1 | Coolify | [Service contribution workflow](https://coolify.io/docs/services) | Compose import and routing guide | Native catalog metadata, generated fields, live test and upstream submission |
| 1 | Dokploy | [Template repository](https://github.com/Dokploy/templates) | Compose import and routing guide | Native catalog metadata, live test and upstream submission |
| 2 | Microsoft / Azure | [Azure Application offer](https://learn.microsoft.com/en-us/partner-center/marketplace-offers/plan-azure-application-offer) | ARM template and Deploy to Azure button | Partner Center publisher account, solution-template offer, portal UI definition/package, live test and certification |
| 2 | Scaleway | [Marketplace partner application](https://www.scaleway.com/en/marketplace/become-partner/) | Instance guide and cloud-init | Confirm distribution format with partner team, package and test it, complete their onboarding |
| 2 | AWS | [AWS Marketplace seller guide](https://docs.aws.amazon.com/marketplace/latest/userguide/user-guide-for-sellers.html) | CloudFormation template | Seller onboarding, choose a supported offer format, build/test an image or container product, submit for review |
| 2 | Google Cloud | [Marketplace partners](https://cloud.google.com/marketplace/docs/partners) | Cloud Shell VM deployment | Partner onboarding, supported product package, technical review and publication |
| Published | Railway | [Public Grovs template](https://railway.com/deploy/grovs-community) | Published template and guide | Complete live deployment tests; approval/verification are separate from publication |
| Available | Render | [Deploy button](https://render.com/docs/deploy-to-render) | Public Blueprint and button | Validate a live deployment; a Blueprint button is not an approved marketplace listing |

There are no Grovs listing URLs for the new cloud providers yet. Replace a console
button with a catalog launch URL only after that listing is public.

## Additional distribution targets

- **Hetzner:** the [Cloud Apps catalog](https://docs.hetzner.com/cloud/apps/overview/)
  uses provider-managed images. An open self-service vendor intake was not found.
  Start with the Grovs guide and propose a useful, reproducible
  [community tutorial](https://community.hetzner.com/). Ask about Cloud Apps inclusion
  before investing in a provider-specific image. Do not invent a `/deploy/grovs` URL.
- **GitHub Marketplace:** accepts Apps and Actions. A real deployment Action could
  qualify; GHCR images and this Compose repository do not constitute a listing.
  See [GitHub Marketplace](https://docs.github.com/en/apps/github-marketplace/github-marketplace-overview/about-github-marketplace-for-apps).
- **Heroku:** requires a separate deployment architecture. Its
  [container runtime](https://devcenter.heroku.com/articles/container-registry-and-runtime)
  has ephemeral storage and does not support Docker volume mounts. Use external
  PostgreSQL, Redis, ClickHouse and object storage, separate backend/dashboard
  web apps, and adapted worker processes. Do not advertise a full-stack button
  until that integration exists.

## Reusable listing copy

**Product name:** Grovs Community

**Short description:** Self-hosted deep linking, attribution and analytics for mobile and web apps.

**Description:**

Grovs Community gives mobile and web teams control of their deep links,
attribution and analytics. Create branded links, direct users to the right app
or website, and measure engagement from a dashboard running in your own cloud
account. The deployment includes the Grovs backend and dashboard, PostgreSQL,
Redis, ClickHouse and background workers. Published container images keep setup
consistent, while persistent volumes store application data. Configure your
own domain, connect the SDKs and start tracking links without building the
application from source. Community Edition requires no enterprise license;
your cloud provider charges for infrastructure. Documentation covers installation,
DNS, HTTPS, credentials, upgrades and backups. Self-hosted Enterprise plans are
available for teams needing additional flexibility and performance.

**Suggested categories:** Analytics, Developer Tools, Marketing (select the closest
categories offered by each catalog).

**Website:** https://www.grovs.io

**Documentation:** https://www.grovs.io/docs/self-hosting/introduction

**Source:** https://github.com/grovs-io/backend

**Deployment source:** https://github.com/grovs-io/self-host

**Community support:** https://github.com/grovs-io/self-host/issues

**Commercial contact:** https://www.grovs.io/contact

Use the provider-specific guide as the installation documentation. For optional
campaign tracking on the website link, use
`?utm_source=digitalocean&utm_medium=marketplace&utm_campaign=community`, replacing
`digitalocean` with the provider slug. Keep the canonical website and repository
links available; don't promise a dofollow link or a ranking improvement.

## Package required for each submission

1. Current backend/dashboard image release and a reviewed deployment-source commit.
2. Full-color and white Grovs SVG logos, screenshots of login and a populated
   dashboard, and any provider-specific artwork dimensions. Capture screenshots
   from demo data and exclude credentials and customer data.
3. A working support URL, publisher contact and the legal/license information
   required by the provider. Take license details from the actual software release.
4. A clean first-boot flow that asks for domain and admin email, generates unique
   secrets per installation, and tells the operator how to retrieve them securely.
5. Evidence from a fresh deployment: migrations, HTTPS, login, project creation,
   live/test links, analytics ingestion, uploads, reboot and backup/restore.
6. Image hygiene for snapshot catalogs: remove credentials, SSH host keys,
   history and instance-specific state using the provider's cleanup tools.
   **Never snapshot an initialized `/opt/grovs/.env` or populated Docker volumes.**
7. Submission ID/PR, reviewer feedback, accepted listing URL and the release tested.

The Azure, cloud-init and [five catalog packages](../../deploy/catalogs/README.md)
have local validation only. No billable cloud instances were created for this
expansion. Image builds, live validation evidence and provider review remain
pending; no new official catalog listing is claimed.
