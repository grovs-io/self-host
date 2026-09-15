# Grovs on Vultr

[Open Vultr Console](https://my.vultr.com/deploy/)

Use a fresh **Ubuntu 24.04 x86_64** server with at least **4 vCPU, 8 GB RAM
and 80 GB SSD**, a public IPv4 address, an SSH key, and a domain you control.
The cloud provider bills your account for the server, storage and traffic.

## Create the instance

1. In Vultr, deploy a **Cloud Compute** server in your chosen region.
2. Select the plain Ubuntu 24.04 image, an x86 plan with the resources above,
   and your SSH public key.
3. Attach a Vultr Firewall group allowing inbound TCP 80/443 from the internet
   and TCP 22 from your public IP. Allow outbound traffic.
4. Deploy and connect with `ssh root@YOUR_SERVER_IP`.
5. Check `sudo ufw status`. If UFW is active, allow ports `80/tcp` and `443/tcp`
   as well, retaining your SSH access.

See [Vultr's firewall guide](https://docs.vultr.com/firewall-quickstart-for-vultr-cloud-servers).

## Install Grovs

Follow the [Ubuntu cloud server setup](cloud-vm.md) over SSH. It installs Docker,
initializes the databases, generates administrator credentials and starts the
stack on reboot. Use the public IPv4 shown in your provider's console for DNS.
