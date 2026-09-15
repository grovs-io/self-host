# Run Grovs yourself

Run the Community Edition in your own account, using the published backend and
dashboard images. The stack includes PostgreSQL, Redis, ClickHouse, background
workers and the dashboard. No Ruby or Node.js build environment is needed.

## Choose where to run it

| You want to… | Start here | What you need |
|---|---|---|
| Try the dashboard and create a link on your laptop | [Local trial](local.md) | Docker with Compose v2 |
| Run the whole stack on your own Linux server | [Docker Compose](server.md) | A server, public IP and domain |
| Manage it from an existing Coolify installation | [Coolify](coolify.md) | A connected server and Traefik with wildcard TLS |
| Manage it from an existing Dokploy installation | [Dokploy](dokploy.md) | A connected server and Traefik with wildcard TLS |
| Create a server in your AWS account | [AWS](aws.md) | AWS billing, deployment permissions and a domain |
| Create a server in your Google Cloud project | [Google Cloud](gcp.md) | Cloud billing, deployment permissions and a domain |
| Create a VM in Azure | [Azure](azure.md) | Subscription, SSH key and domain |
| Run on DigitalOcean | [DigitalOcean](digitalocean.md) | Cloud account, SSH key and domain |
| Run on Hetzner | [Hetzner](hetzner.md) | Cloud account, SSH key and domain |
| Run on Vultr | [Vultr](vultr.md) | Cloud account, SSH key and domain |
| Run on Akamai / Linode | [Akamai / Linode](akamai.md) | Cloud account, SSH key and domain |
| Run on Scaleway | [Scaleway](scaleway.md) | Cloud account, SSH key and domain |
| Run services in a Railway project | [Deploy on Railway](https://railway.com/deploy/grovs-community) · [Guide](railway.md) | Railway account, billing, domains and object storage |
| Run services on Render | [Render Blueprint](render.md) | Render account, billing, domain and object storage |

**For the shortest server setup, choose Docker Compose.** Coolify and Dokploy
reuse your platform's proxy. The AWS and Google Cloud options create one VM and
run the standalone Compose stack on it. Cloud Shell is the deployment terminal;
it is not where Grovs runs.

## What setup does for you

- Pulls matching, versioned images from public GHCR packages.
- Generates database passwords, encryption keys, OAuth credentials and an admin login.
- Creates persistent volumes for databases and uploaded files.
- Runs PostgreSQL and ClickHouse migrations before starting the API and workers.

You supply domains and an admin email. For a public installation, you also point
DNS at your server and configure TLS. Local trials use `lvh.me` over HTTP.

Your server and storage are paid for through your infrastructure provider. The
Community Edition does not require an enterprise license. SMTP is optional for
initial login; configure it later for email-based password resets and notifications.

## First successful deployment

1. Open the dashboard and log in with the generated admin credentials.
2. Create a project and a link, then open the link in your browser.
3. Wait for the first analytics rollup and check that the event appears.
4. [Configure your SDKs](../../README.md#configure-the-sdks) with the project's API key
   and your own SDK host.
5. Save `.env` securely and arrange [backups](../../README.md#backups).
