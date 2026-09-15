# Publish and maintain deployment options

This is the maintainer checklist for turning the checked-in templates into
public deployment entry points. Do this for the Community Edition after the
matching backend/dashboard GHCR release is available.

## Validate the repository

```bash
python3 scripts/generate-platform-compose.py --check
python3 scripts/generate-paas.py --check
python3 -m unittest discover -s tests -v
cfn-lint deploy/aws/cloudformation.yaml
npm --prefix .railway ci
npm --prefix .railway run check
npm --prefix .railway test
```

Install Docker Compose v2 and `cfn-lint` before running these checks. The tests
use generated temporary environment files. They validate Compose
rendering and routing, secret generation and preservation, and cloud command
construction without creating cloud resources. They do not prove that DNS,
certificates, IAM or the application work on a real platform.

Whenever `docker-compose.yml` or `.env.example` changes, regenerate
`docker-compose.platform.yml` with `python3 scripts/generate-platform-compose.py`.
Keep the generated file committed so a panel can deploy it directly.
Regenerate `render.yaml` and `deploy/paas/commands.json` with
`python3 scripts/generate-paas.py` when the defaults or PaaS startup script change.
Validate `render.yaml` against [Render's published schema](https://render.com/schema/render.yaml.json)
or with the Render CLI before release.

## Publish files and images

1. Publish the same release tag for both application images, including the
   architectures you support. Verify anonymous pulls with a clean Docker config.
2. Publish this self-host repository's changes. The cloud tutorial and bootstrap
   paths must exist publicly before their links can work.
3. Pin the stack reference to a reviewed commit or new self-host release tag.
   Existing releases predating `deploy/` cannot run the new cloud bootstrap.
4. Deploy a fresh instance on each target and test login, link creation, wildcard
   production/test links, HTTPS association endpoints and analytics ingestion.
5. Test a reboot, an upgrade, and a backup/restore. Record the platform version,
   image release and result before advertising the option as verified.

## Google Cloud button

The docs already link to the Cloud Shell tutorial. Once these files are public,
this Markdown provides the same entry point anywhere:

```markdown
[Deploy on Google Cloud](https://ssh.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fgrovs-io%2Fself-host&cloudshell_tutorial=deploy%2Fgcp%2Ftutorial.md)
```

The tutorial asks users to select a billing-enabled project and explicitly
confirm resource creation. [Google's button documentation](https://docs.cloud.google.com/shell/docs/open-in-cloud-shell)

## AWS Launch Stack button

Upload the reviewed template to an S3 location that CloudFormation can read.
Use a versioned object key, then generate the link:

```bash
aws s3 cp deploy/aws/cloudformation.yaml s3://YOUR_TEMPLATE_BUCKET/grovs/RELEASE/cloudformation.yaml
./deploy/aws/launch-link.sh us-east-1 \
  https://YOUR_TEMPLATE_BUCKET.s3.us-east-1.amazonaws.com/grovs/RELEASE/cloudformation.yaml
```

Configure read access for that template object according to your distribution
policy; the upload command alone does not make it public. Use the resulting URL
as the target of an AWS deployment button. It opens the CloudFormation review
form with the template selected. The README's AWS link currently opens the
guide, so it does not point at a nonexistent S3 object.
[AWS quick-create documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stacks-quick-create-links.html)

## Coolify and Dokploy catalogs

The current instructions import a Compose definition into the user's own
installation. There is no single universal URL for everyone's private control
panel. The README links to the guides and does not claim a catalog listing.

After a live deployment passes, package each platform's required catalog metadata
and submit its template upstream. Review the current
[Coolify service workflow](https://coolify.io/docs/services) and
[Dokploy template contribution guide](https://github.com/Dokploy/templates).
Keep credential-generation fields and domain questions synchronized with the
shared setup script. Catalog submission is a separate publishing step.

## Render and Railway

The Render deploy link reads the root `render.yaml` from the public repository.
Publish it with the matching images, test the complete domain/storage/login flow,
and then advertise it as verified. [Render button documentation](https://render.com/docs/deploy-to-render)

Railway's IaC definition is usable through its CLI. A marketplace button still
requires creating and publishing a Railway template. Follow the
[Railway setup guide](railway.md) to deploy a project, then select **Project
Settings → Generate Template from Project**. Replace literal secrets with
template-generated values and service references, and test that two fresh
deployments receive different secrets. See [Creating Railway templates](https://docs.railway.com/templates/create). Add the actual published template URL to the README
and documentation site after this check.
