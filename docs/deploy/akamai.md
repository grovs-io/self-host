# Grovs on Akamai / Linode

[Open Akamai / Linode Console](https://cloud.linode.com/linodes/create)

Use a fresh **Ubuntu 24.04 x86_64** server with at least **4 vCPU, 8 GB RAM
and 80 GB SSD**, a public IPv4 address, an SSH key, and a domain you control.
The cloud provider bills your account for the server, storage and traffic.

## Create the Linode

1. In Cloud Manager, create a Linode using the plain **Ubuntu 24.04** image.
2. Choose a region and an x86 plan meeting the resources above. Add your SSH
   public key and provide the operating-system credentials required by the form.
3. Attach a Cloud Firewall allowing inbound TCP 80/443 from the internet and
   TCP 22 only from your public IP. Allow outbound traffic.
4. Create the Linode and connect with `ssh root@YOUR_SERVER_IP`.

## Install Grovs

Follow the [Ubuntu cloud server setup](cloud-vm.md) over SSH. It installs Docker,
initializes the databases, generates administrator credentials and starts the
stack on reboot. Use the public IPv4 shown in your provider's console for DNS.
