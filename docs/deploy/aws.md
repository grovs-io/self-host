# Deploy on AWS

The [CloudFormation template](../../deploy/aws/cloudformation.yaml) creates a
dedicated VPC, public subnet, security group, static IPv4 address and one Ubuntu
24.04 EC2 instance. Grovs runs on that instance using Docker Compose. PostgreSQL,
Redis, ClickHouse and uploads use persistent Docker volumes on its encrypted EBS
disk. This is a single-server deployment, not an HA cluster.

**You pay AWS for the instance, EBS storage and public IPv4.** The default is a
`t3.xlarge` with 100 GiB of gp3 storage. Review regional pricing before creating it.

## Launch from the AWS console

1. Download `deploy/aws/cloudformation.yaml` from this repository.
2. Open **CloudFormation → Create stack → With new resources** in your chosen
   region. Select **Upload a template file** and upload it.
3. Fill in `AppDomain`, `AdminEmail` and a published `GrovsVersion`.
4. Keep `StackRef=main` or pin a reviewed commit containing the deployment files.
   The historical `2.3.0` self-host tag does not contain these new cloud scripts.
5. Review the resources and acknowledge IAM creation. The instance role grants
   Session Manager connectivity; no SSH port is open publicly.
6. Create the stack. Copy `IpAddress` and `InstanceId` from Outputs.

Your AWS identity needs permissions for the resources in the template, IAM role
creation/pass-role, and reading the public Ubuntu AMI parameter from SSM.

CloudFormation completion means the VM has been created. **Application setup
continues inside it**; allow time for package installation, image pulls and
migrations before expecting a dashboard.

## DNS, credentials and readiness

Point the [Grovs DNS records](server.md#2-configure-dns) at the static IP. In
**EC2 → Instances → Connect → Session Manager**, open the instance and run:

```bash
sudo systemctl status grovs --no-pager
sudo tail -100 /var/log/cloud-init-output.log
sudo cat /opt/grovs/.env
```

Use `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` to sign in at
`https://dashboard.<AppDomain>`. Setup writes secrets to root-readable files;
they are not stored in CloudFormation parameters or Outputs.

If Session Manager is unavailable, verify the instance profile, outbound network
access and SSM agent status. The operator also needs permission to start an SSM
session. [AWS Session Manager prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html)

Finish the checks in [First successful deployment](README.md#first-successful-deployment).

## Operate and remove

The checkout and `.env` live in `/opt/grovs`. `grovs.service` starts the stack on
boot. Use `sudo -i`, then `cd /opt/grovs` for the usual Compose commands.

Back up PostgreSQL, ClickHouse, uploads and `.env` before upgrades. Updating the
CloudFormation parameters is not a supported in-place application upgrade;
follow the [application upgrade procedure](../../README.md#upgrades).

Deleting the CloudFormation stack terminates the VM and releases its public IP.
The root EBS volume is **retained** (`DeleteOnTermination: false`) so its data is
not erased with the instance. It continues to incur storage charges. Identify
and snapshot that volume before deletion; deleting retained volumes is a
separate, irreversible operation. A retained disk is not a database backup.
