# Grovs on Azure

[Deploy to Azure](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fgrovs-io%2Fself-host%2Fmain%2Fdeploy%2Fazure%2Fazuredeploy.json)

Deploy the full Grovs Community stack on one Ubuntu 24.04 VM in your Azure
subscription. The template creates a virtual network, restricted SSH access,
a static public IPv4 address, and a persistent disk. The default VM is
`Standard_D4s_v5` with 4 vCPU, 16 GiB RAM and a 128 GiB disk.
**Azure bills your subscription for these resources.**

## Deploy through the portal

1. Click **Deploy to Azure**. Choose your subscription, a new resource group and
   a region where the VM size is available. Your account needs permission to
   create compute and network resources in that group.
2. Enter your app domain, such as `grovs.example.com`, and administrator email.
3. Paste your **SSH public key** (the contents of your `.pub` file).
4. Set `sshSourceCidr` to your public IPv4 followed by `/32`; this restricts SSH
   to your workstation. Leave `adminUsername` as `grovsadmin` unless needed.
5. Review the VM size, disk, image release and resource costs, then create.
6. Open the deployment's **Outputs** for the IP address and SSH command.

[Review the template](https://github.com/grovs-io/self-host/tree/main/deploy/azure)
before deploying. The form defaults to published release `2.3.1` and a pinned
Compose source commit. VM creation can finish before application setup does.

## DNS and first login

Point the [DNS records](../../README.md#dns) at the public IP in Outputs.
SSH with the printed command, then:

```bash
sudo cloud-init status --wait
sudo tail -100 /var/log/cloud-init-output.log
sudo systemctl status grovs --no-pager
sudo docker compose --project-directory /opt/grovs ps -a
sudo cat /opt/grovs/.env
```

Open `https://dashboard.grovs.example.com` and sign in with
`BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from `.env`.
Keep that file private. Create a project and link, open the link, and confirm
analytics before connecting your applications.

## Maintain or remove the deployment

`grovs.service` restarts the existing stack on reboot. Follow
[upgrades](../../README.md#upgrades) and [backups](../../README.md#backups)
from `/opt/grovs` using root access. An ARM deployment marked successful does
not prove that migrations or DNS have completed; check the commands above.

Back up databases, uploads and `.env` outside Azure's resource group before
removal. Deleting only the VM detaches and retains its OS/data disk; retained
disks and IPs can continue billing. **Deleting the resource group deletes the
disk and its Grovs data too.** Review the remaining resources in Azure before
removing anything else.
