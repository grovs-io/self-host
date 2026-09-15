packer {
  required_plugins {
    vultr = {
      source  = "github.com/vultr/vultr"
      version = "~> 2"
    }
  }
}
variable "api_token" {
  type      = string
  default   = env("VULTR_API_KEY")
  sensitive = true
}
source "vultr" "grovs" {
  api_key              = var.api_token
  os_id                = "2284"
  plan_id              = "vc2-4c-8gb"
  region_id            = "fra"
  ssh_username         = "root"
  snapshot_description = "Grovs Community 2.3.1 ${formatdate("YYYYMMDDhhmm", timestamp())}"
  state_timeout        = "25m"
}
build {
  sources = ["source.vultr.grovs"]
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
  provisioner "file" {
    source      = "${path.root}/setup-per-instance.sh"
    destination = "/opt/grovs-catalog-input/setup-per-instance.sh"
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
