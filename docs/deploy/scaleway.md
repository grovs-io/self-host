# Grovs on Scaleway

[Open Scaleway Console](https://console.scaleway.com)

Use a fresh **Ubuntu 24.04 x86_64** server with at least **4 vCPU, 8 GB RAM
and 80 GB SSD**, a public IPv4 address, an SSH key, and a domain you control.
The cloud provider bills your account for the server, storage and traffic.

## Create the Instance

1. In your Scaleway project, create an x86 Instance with the plain Ubuntu 24.04
   image and the resources above. Choose a persistent root volume.
2. Assign a public IPv4 address and add your SSH public key.
3. Configure the Instance's security group to allow inbound TCP 80/443 from the
   internet and TCP 22 only from your public IP. Allow outbound traffic.
4. Start the Instance and connect with `ssh root@YOUR_SERVER_IP`.

See Scaleway's [Instance creation guide](https://www.scaleway.com/en/docs/instances/how-to/create-an-instance/).

## Install Grovs

Follow the [Ubuntu cloud server setup](cloud-vm.md) over SSH. It installs Docker,
initializes the databases, generates administrator credentials and starts the
stack on reboot. Use the public IPv4 shown in your provider's console for DNS.

## Automate first boot

For a fresh Instance that has not started yet, you can instead generate startup
data on your workstation:

On your workstation, generate startup data with your domain and administrator email:

```bash
git clone https://github.com/grovs-io/self-host.git
cd self-host
python3 scripts/generate-cloud-init.py \
  --domain grovs.example.com \
  --email admin@example.com > /tmp/grovs-cloud-init.yaml
```

The file installs Docker and the full Compose stack on first boot. It pins the
stack source to a reviewed commit and defaults to image release `2.3.1`. Use
`--version X.Y.Z` to select another published release. Passwords are generated on
the server; the startup file contains no generated credentials.

With the Scaleway CLI configured for the correct project and zone, attach the
file **before the first boot**, replacing `SERVER_ID` with your Instance ID:

```bash
scw instance server update SERVER_ID cloud-init=@/tmp/grovs-cloud-init.yaml
scw instance server start SERVER_ID
```

Then follow [DNS and first login](cloud-vm.md#dns-and-first-login).
See Scaleway's [cloud-init instructions](https://www.scaleway.com/en/docs/instances/how-to/use-cloud-init/).
