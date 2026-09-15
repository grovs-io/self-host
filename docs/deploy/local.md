# Try Grovs locally

Use this to explore the dashboard, create projects and test link tracking without
a public server or DNS setup. Install Docker with Docker Compose v2 first. On
Windows, run the commands from WSL2 with Docker integration enabled.

## Start with the installer

Run this from the directory where you want the new `grovs` folder:

```bash
curl -fsSL https://raw.githubusercontent.com/grovs-io/self-host/main/install.sh | GROVS_DOMAIN=local bash
cd grovs
```

The installer downloads the Compose files, generates your admin login and starts
all services. `GROVS_DOMAIN=local` selects the local trial without asking for a
domain. It uses the release version bundled with the installer.

Open **http://dashboard.lvh.me:3002**. Use the admin email and password printed by
setup. `lvh.me` and its subdomains resolve to `127.0.0.1`; they point at your own
machine. The API uses port 80 by default.

If port 80 is already in use, add `GROVS_WEB_PORT=8080` before `bash` in the
installer command, using a fresh directory. The dashboard port can likewise be changed with
`GROVS_DASHBOARD_PORT`. Settings are saved in `.env`.

## Manual setup (alternative)

To clone and inspect the repository yourself, use these commands instead of the
installer, in a fresh directory:

```bash
git clone https://github.com/grovs-io/self-host.git grovs
cd grovs
GROVS_DOMAIN=local ./scripts/setup.sh
docker compose -f docker-compose.yml -f docker-compose.local.yml pull
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

For an existing installation, follow the [upgrade procedure](../../README.md#upgrades) rather than rerunning the installer.

## Check startup

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml ps -a
docker compose -f docker-compose.yml -f docker-compose.local.yml logs --tail=100 migrate web
curl --fail http://api.lvh.me/up
```

Use `http://api.lvh.me:8080/up` if you selected port 8080. The `migrate` service
should finish with exit code 0; it is not supposed to remain running. Analytics
can take about a minute after startup to become available.

Local HTTP is suitable for a trial. Mobile Universal Links and App Links need a
public HTTPS installation: follow [Run on a server](server.md). A phone's
`127.0.0.1` refers to the phone, not your laptop.

## Stop and resume

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml stop
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

Both commands preserve your data. To permanently remove the trial and **delete
all its database and upload volumes**:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down --volumes
```
