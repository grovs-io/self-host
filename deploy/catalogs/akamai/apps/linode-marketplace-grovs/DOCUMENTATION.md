# Deploy and operate Grovs Community

Select Ubuntu 24.04 with at least 4 vCPU, 8 GB RAM and 80 GB SSD. Supply these
StackScript fields:

| Field | Value |
|---|---|
| App domain | A public domain without `https://`, such as `grovs.example.com` |
| First administrator email | Your email for the Grovs dashboard login |
| SSH administrator username | A new Linux user, default `grovsadmin` |
| SSH public key | Your public Ed25519, RSA or ECDSA P-256 key |
| SSH source | Your public IPv4 followed by `/32` |

Keep the matching private SSH key on your computer. The installer creates the
operator with sudo access, disables password/root SSH login and restricts SSH
through the host firewall to the supplied IP. If your address changes, use the
provider's console to update the firewall rule.

## DNS and login

Point the records in the [Grovs DNS guide](https://github.com/grovs-io/self-host#dns)
at the server's public IP. For `grovs.example.com`, include the fixed application
hosts, `*.grovs.example.com` and `*.test.grovs.example.com`. Keep ports 80 and 443
reachable so Caddy can obtain certificates and serve requests.

Connect as your new operator after provisioning completes:

```bash
ssh grovsadmin@YOUR_SERVER_IP
cat ~/.credentials
sudo systemctl status grovs --no-pager
```

The credentials file contains your dashboard URL, admin email and generated
password. Keep it private. Sign in, create a project and a link, open the link,
then check its analytics. Connect your app with the project's SDK key and
`https://sdk.YOUR_APP_DOMAIN`.

## Troubleshooting and maintenance

Inspect `/var/log/stackscript.log` for provisioning errors if present, and
`sudo journalctl -u grovs` for service startup. Application setup details are in
`/opt/grovs/setup.log`; configuration and encryption keys are in
`/opt/grovs/.env`, accessible only with root privileges.

```bash
sudo docker compose --project-directory /opt/grovs ps -a
sudo docker compose --project-directory /opt/grovs logs --tail=100 migrate web
```

The migration container should exit successfully; workers and application
services stay running. `grovs.service` starts the stack after reboot. Follow
[upgrades](https://github.com/grovs-io/self-host#upgrades) and
[backups](https://github.com/grovs-io/self-host#backups) using root access in
`/opt/grovs`. Preserve `.env` and Docker volumes. Back up outside this server
before deleting a Linode or its disk.

Community support: https://github.com/grovs-io/self-host/issues
