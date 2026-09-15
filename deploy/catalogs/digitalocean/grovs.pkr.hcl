packer {
  required_plugins {
    digitalocean = {
      source  = "github.com/digitalocean/digitalocean"
      version = "~> 1"
    }
  }
}
variable "api_token" {
  type      = string
  default   = env("DIGITALOCEAN_TOKEN")
  sensitive = true
}
source "digitalocean" "grovs" {
  api_token     = var.api_token
  image         = "ubuntu-24-04-x64"
  region        = "fra1"
  size          = "s-4vcpu-8gb"
  ssh_username  = "root"
  snapshot_name = "grovs-community-2.3.1-${formatdate("YYYYMMDDhhmm", timestamp())}"
}
build {
  sources = ["source.digitalocean.grovs"]
  provisioner "shell" {
    inline = ["cloud-init status --wait", "mkdir -p /opt/grovs-catalog-input"]
  }
  provisioner "file" {
    source      = "${path.root}/../shared/"
    destination = "/opt/grovs-catalog-input/"
  }
  provisioner "file" {
    source      = "${path.root}/../../vm/bootstrap.sh"
    destination = "/opt/grovs-catalog-input/bootstrap.sh"
  }
  provisioner "shell" {
    environment_vars = ["GROVS_IMAGE_BUILD=1"]
    script           = "${path.root}/../shared/prepare-image.sh"
  }
  provisioner "shell" {
    environment_vars = ["GROVS_IMAGE_BUILD=1"]
    script           = "${path.root}/finalize-image.sh"
  }
}
