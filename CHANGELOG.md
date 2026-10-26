# Changelog

All notable changes to the Grovs self-hosted stack are documented here. Each
version runs the backend and dashboard images of the same version.

## [3.0.0] - 2026-10-26

### Upgrade notes

Back up the databases, uploads and `.env` first, then follow
[Upgrades](README.md#upgrades) with `GROVS_VERSION=3.0.0`. The `migrate` step
applies the new Postgres and ClickHouse migrations.

- Existing installs: add a `TRUSTED_PROXY_SECRET` to `.env` so the backend sees
  users' real IPs on login (new installs get one from `scripts/setup.sh`):

  ```bash
  echo "TRUSTED_PROXY_SECRET=$(openssl rand -hex 32)" >> .env
  ```

- Custom events named `push_open`, `push_delivered`, `push_held`, `in_app_*` or
  `journey_*` are now rejected by the backend; rename them in your apps. See the
  [backend changelog](https://github.com/grovs-io/backend/blob/main/CHANGELOG.md).

### Added

- Backend and dashboard 3.0.0: segments, push campaigns, in-app messages,
  journeys and event streaming in the Enterprise Edition; smart banners, custom
  dashboards and guided project setup in every edition.
- `worker-2` also runs the event-streaming, push, in-app and journey queues and
  the push daemon when the image carries the Enterprise Edition. The Community
  image is unchanged.
- `scripts/setup.sh` generates `TRUSTED_PROXY_SECRET` and the dashboard passes it.

### Changed

- Railway, Render, Dokploy, Easypanel, CapRover and the platform Compose file are
  regenerated from these sources.
- `LICENSE` names Appssemble Soft SRL as the copyright holder.

## [2.3.1] and earlier

See the [GitHub releases](https://github.com/grovs-io/self-host/releases).

[3.0.0]: https://github.com/grovs-io/self-host/compare/2.3.1...3.0.0
[2.3.1] and earlier: https://github.com/grovs-io/self-host/releases
