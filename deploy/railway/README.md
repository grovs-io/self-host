# Deploy and Host Grovs Community on Railway

Self-host Grovs for deep links, mobile attribution, referrals and analytics using
the official Community images. Your deployment includes the dashboard, API, two
workers, PostgreSQL, Redis and ClickHouse with persistent database volumes.

## About Hosting Grovs Community

The services run from versioned container images. PostgreSQL stores application
data, ClickHouse stores analytics and Redis supports background jobs. The API
initializes schemas before starting, and workers wait for its health endpoint.

## Why Deploy Grovs Community on Railway

Railway brings the application and database services into one project with
private networking, persistent volumes, deployment logs and HTTPS endpoints.
This template wires the services together and generates their shared secrets.

## Common Use Cases

- Deep links that open the right screen in an installed app.
- Attribution for mobile campaigns and referrals.
- Analytics for links and app events under your own account.

## Dependencies for Grovs Community

- Use the Hobby or Pro plan. The Trial plan allows only 5 services per project;
  Grovs needs 7. Hobby allows 2 custom domains per service, so it uses the
  compact domain layout below. Compute, volumes and network usage are billed by
  Railway.
- Bring a private S3-compatible bucket and bucket-scoped credentials for uploads.
  For Amazon S3 leave `S3_ENDPOINT` empty; for another provider set it to the
  provider's S3 API endpoint.
- Choose an app base domain and production/test link base domains you control.

For example, set `SERVER_HOST=grovs.example.com`,
`DOMAIN_LIVE=links.example.com` and `DOMAIN_TEST=test.links.example.com`.
Enter these without a protocol, wildcard or path. Set your admin email and the
four required S3 variables on `web`. Railway generates separate secrets for each
deployment and shares them with the workers and dashboard through references.

## Finish setup

1. Keep all services in one Railway region. Size database volumes for your data
   and retention, especially ClickHouse. Keep both workers always running.
2. The API pre-deploy command initializes the database schemas and admin login.
   If databases are still starting, wait for them to be ready and redeploy `web`.
3. In Railway Networking, add these custom domains, all targeting port **3000**:
   - `dashboard`: `dashboard.grovs.example.com`
   - `web` on Pro: `api.grovs.example.com`, `sdk.grovs.example.com`,
     `mcp.grovs.example.com`, `go.grovs.example.com`, `preview.grovs.example.com`,
     `*.links.example.com` and `*.test.links.example.com`
   - `web` on Hobby: `*.grovs.example.com` and `*.links.example.com`. Test links
     are not served until you add `*.test.links.example.com` on Pro.
4. Add every record Railway shows for each domain at your DNS provider: the
   CNAME, an `_acme-challenge` CNAME for wildcards and the `_railway-verify`
   TXT record. Certificates are not issued until the TXT record exists. Use
   your custom domains for Grovs login and links.
5. Sign in at `https://dashboard.grovs.example.com` using `BOOTSTRAP_ADMIN_EMAIL`
   and the generated `BOOTSTRAP_ADMIN_PASSWORD` in `web`'s variables.
6. Check the API `/up` endpoint, create a project, open production and test links,
   verify analytics and upload an image.

## Updates

Back up PostgreSQL, ClickHouse, uploads and configuration before upgrading. Stop
both workers, update the API image to the desired published version and let its
migrations finish. Update the dashboard and both workers to the same version,
then restart them. Keep `worker-1` at **one instance**, including during rollouts,
because it owns the scheduler.

This template has been deployed end to end on Railway: migrations, workers,
custom domains with wildcard HTTPS, sign-in, project links, uploads and
analytics.

- [Full Railway guide](https://github.com/grovs-io/self-host/blob/main/docs/deploy/railway.md)
- [Source and deployment configuration](https://github.com/grovs-io/self-host)
- [Grovs](https://www.grovs.io)
