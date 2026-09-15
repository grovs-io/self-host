# Local validation record — 15 September 2026

No paid cloud resources were created. These checks do not test a deployed Grovs
installation, TLS issuance or provider metadata delivery.

| Check | Result |
|---|---|
| Repository Python tests | 34 passed, including generated-file freshness, migration failure propagation, secrets, persistence and Ansible input validation |
| CapRover upstream `validate_apps` and `build` | Passed with the candidate copied into the upstream tree |
| Easypanel template generation, TypeScript and Zod schema checks | Passed with the candidate copied into the upstream tree |
| DigitalOcean Packer recipe | `packer init` and `packer validate` passed with a dummy token; no `build` run |
| Vultr Packer recipe | `packer init` and `packer validate` passed with a dummy token; no `build` run |
| Shell scripts | Bash syntax and ShellCheck 0.11.0 passed |
| Ansible | Syntax checks passed; input-only playbook accepts valid fields and rejects missing domain, root user and an invalid IP |
| Public panel images | Anonymous manifest lookup succeeded for backend/dashboard 2.3.1, PostgreSQL 16.10-alpine, Redis 7.4.5-alpine and ClickHouse 25.3.6.56 |

Upstream revisions checked:

- Easypanel templates: `647714de6c7c285561316628dabd6303fbbfaeb4`.
- CapRover One Click Apps: `43f049e5a0d8eb1779481a839640ba00203d131f`.
- Packer 1.14.2, DigitalOcean plugin 1.4.1, Vultr plugin 2.7.0.
- Ansible core 2.18.4.

## Still pending

- Build and launch DigitalOcean/Vultr marketplace images, confirm cleanup and
  unique instance identity, and complete vendor onboarding.
- Execute the Ansible installer on Ubuntu in a new Linode.
- Import and start the panel templates in actual Easypanel/CapRover instances.
- Verify wildcard HTTPS, migrations against real databases, dashboard login,
  project links, event ingestion, uploads, reboot and backup/restore.
- Capture genuine application screenshots, submit packages for provider review
  and record resulting catalog URLs.

Use [the provider instructions](README.md) for the next steps. Do not mark a
provider's live-testing checklist complete based on this local record.
