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

To install on the Instance's first boot instead of over SSH, copy the startup
block from [Install on first boot](cloud-vm.md#install-on-first-boot), replace
the example domain and email, and add it as cloud-init user data before the
Instance first starts. If you use the Scaleway CLI, save the block as
`grovs-cloud-init.yaml` and attach it, replacing `SERVER_ID` with your Instance ID:

```bash
scw instance server update SERVER_ID cloud-init=@grovs-cloud-init.yaml
scw instance server start SERVER_ID
```

Then follow [DNS and first login](cloud-vm.md#dns-and-first-login).
See Scaleway's [cloud-init instructions](https://www.scaleway.com/en/docs/instances/how-to/use-cloud-init/).
