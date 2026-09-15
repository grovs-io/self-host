# Deploy on Google Cloud

[Open the guided Cloud Shell deployment](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgrovs-io%2Fself-host&cloudshell_tutorial=deploy%2Fgcp%2Ftutorial.md)

The script creates a dedicated VPC and subnet, static public IPv4, HTTP/HTTPS
firewall rules, an IAP-only SSH rule and one Ubuntu 24.04 VM. It runs the full
Compose stack on that VM. The default is `e2-standard-4` with a 100 GB persistent
boot disk. **These are billable Google Cloud resources.**

## Before starting

Use a billing-enabled project. Your identity needs permission to enable the
Compute API and create Compute Engine networking, disks and instances. For
administrative access, use OS Admin Login and IAP tunnel permissions. The VM has
no service account and no Google API scopes; it pulls public images without
cloud credentials.

See Google's [IAP TCP forwarding setup](https://cloud.google.com/iap/docs/using-tcp-forwarding)
and [OS Login setup](https://cloud.google.com/compute/docs/oslogin/set-up-oslogin).

## Deploy from Cloud Shell or your workstation

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
./deploy/gcp/deploy.sh YOUR_PROJECT_ID europe-west1-b example.com admin@example.com 2.3.0
```

The script shows the target project, zone and machine type before requesting
confirmation. It passes `--project` explicitly and does not change your gcloud
default project. Set `GROVS_INSTANCE_NAME` for another installation name and
`GROVS_MACHINE_TYPE` for a different machine size.

For a repeatable install, set `GROVS_STACK_REF` to a reviewed self-host commit
containing these deployment files. Application images use the release passed as
the last argument; `GROVS_STACK_REF` selects the Compose files and setup scripts.

Point the [DNS records](server.md#2-configure-dns) at the printed static IP.
Package installation and migrations continue after VM creation. Use the SSH
command printed by the script, then:

```bash
sudo journalctl -u google-startup-scripts.service --no-pager -n 100
sudo systemctl status grovs --no-pager
sudo cat /opt/grovs/.env
```

Open `https://dashboard.<your-domain>` and sign in with the bootstrap admin values
from `.env`. Then [verify the deployment](README.md#first-successful-deployment).

## Restarts and upgrades

`grovs.service` starts the existing stack on reboot. Bootstrap preserves an
existing checkout and `.env`; it does not regenerate secrets or change the
application version. Follow the [upgrade procedure](../../README.md#upgrades)
from `/opt/grovs` using root access.

## Failed or partial deployments

The script stops at the first failed cloud command. It does not automatically
delete resources already created. Inspect the named resources before retrying;
an existing name causes `create` to fail instead of replacing your installation.
Use the commands below to remove a partial deployment, or finish provisioning
manually. If VM startup failed, fix the reported issue before rerunning bootstrap.

## Remove the deployment

Back up your data and `.env` first. Replace the values below if you chose a
different project, name or location:

```bash
PROJECT=YOUR_PROJECT_ID
ZONE=europe-west1-b
REGION=europe-west1
NAME=grovs
gcloud --project="$PROJECT" compute instances delete "$NAME" --zone="$ZONE"
gcloud --project="$PROJECT" compute addresses delete "$NAME-ip" --region="$REGION"
gcloud --project="$PROJECT" compute firewall-rules delete "$NAME-web" "$NAME-ssh"
gcloud --project="$PROJECT" compute networks subnets delete "$NAME-subnet" --region="$REGION"
gcloud --project="$PROJECT" compute networks delete "$NAME-network"
```

The boot disk is **retained** and continues to incur storage charges. List it with
`gcloud --project="$PROJECT" compute disks list`, snapshot it if needed, and delete
it separately only when you no longer need the data. A retained disk is not a
database backup.
