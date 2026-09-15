# Deploy Grovs Community on Google Cloud

This guide creates one Ubuntu VM running the full Grovs stack. You pay Google
Cloud for the VM, disk and public IP. Allow roughly 10 minutes plus DNS propagation.

## Choose your project

<walkthrough-project-setup></walkthrough-project-setup>

Use a project with billing enabled and permission to create Compute Engine
networks, firewalls, static IPs and VMs. You also need OS Admin Login and IAP tunnel
access to retrieve the initial administrator password.

## Deploy

In the terminal, change to the cloned `self-host` directory if needed. Replace
the project, zone, domain and email below with your values:

```bash
./deploy/gcp/deploy.sh YOUR_PROJECT_ID europe-west1-b example.com admin@example.com 2.3.0
```

Review the resources shown by the script and confirm. It generates secrets on
the VM and prints its static IP. Keep the domain as a bare hostname, without
`https://` or a path.

## Point DNS at the VM

Create A records for `dashboard`, `api`, `sdk`, `mcp`, `go`, `preview`, `links`,
`links.test`, `*` and `*.test` under your domain, all pointing to the printed IP.
Use DNS-only records initially. See [DNS and TLS](../../docs/deploy/server.md).

## Sign in

Use the SSH command printed by the deployment script. Then run:

```bash
sudo systemctl status grovs --no-pager
sudo cat /opt/grovs/.env
```

Use `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` at
`https://dashboard.<your-domain>`. Do not share the other secrets in that file.
Create a project and a link, open the link, then check analytics.

## Operate or remove the deployment

Follow [Google Cloud operations and cleanup](../../docs/deploy/gcp.md).
The boot disk is retained when the VM is deleted, and continues to incur storage
charges until you delete it separately. Back up the databases and `.env` first.
