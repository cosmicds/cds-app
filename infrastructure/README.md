# Terraform Layout

This directory now uses isolated Terraform roots per environment:

- `environments/demo`
- `environments/staging`
- `environments/production`
- `environments/delivery`

`demo` is a standalone, Hubble-only deployment. It has its own VPC, ALB,
CloudFront distribution, ECS cluster, ECR repository, build pipeline, secret,
and Terraform state. It does not depend on the full production or staging
stacks. The default configuration runs one 0.5-vCPU/1-GB Fargate task with no
autoscaling, NAT gateways, portal service, or Container Insights.

`staging` and `production` each provision a separate application stack from
`modules/app_stack`, so Terraform state and infrastructure are isolated.

`delivery` provisions the shared ECR repositories and CodePipeline workflow from
`modules/release_pipeline`. The pipeline builds once, deploys to staging first,
waits for manual approval, and then deploys to production. Its naming prefix is
kept aligned with the historical production stack so existing delivery
resources can be migrated without replacement.

## Usage

Run Terraform from the specific environment directory:

```sh
cd infrastructure/environments/staging
terraform init
terraform plan
```

Review the checked-in `terraform.tfvars` for the selected root before planning.
Repeat the same pattern for `demo`, `production`, and `delivery`.

## Demo Bootstrap

The demo task reads the same Hubble secret keys as staging and production,
plus `CDS_FORCE_DEMO` and `CDS_DISABLE_DB`, from the independent
`demo/cds-hubble/secrets` Secrets Manager secret. Terraform creates the secret
container but deliberately does not manage its value. Bootstrap it before the
full deployment:

```sh
cd infrastructure/environments/demo
terraform init
terraform apply -target=aws_secretsmanager_secret.hubble
```

Copy the JSON value from `production/cds-hubble/secrets` into the demo secret,
then add these entries:

```json
{
  "CDS_FORCE_DEMO": "true",
  "CDS_DISABLE_DB": "true"
}
```

Every mapped key must exist in the demo secret or ECS will reject the task at
startup. Before deploying, update environment-specific values such as
`SOLARA_ROOT_PATH`, `SOLARA_BASE_URL`, and `AWS_EBS_URL` for the root-mounted
demo and its initial CloudFront hostname.

Then run `terraform plan` and `terraform apply` from the same directory. The
new CodeStar connection must be authorized in the AWS console before the demo
pipeline can access GitHub. Start the pipeline once to create the initial
`cds-hubble-demo:latest` image; the ECS service will not stabilize until that
image exists.

The demo initially uses its generated CloudFront hostname because a hostname
can only be attached to one CloudFront distribution at a time. After the old
production distribution is retired, set `site_domain_name` to
`app.cosmicds.cfa.harvard.edu`, set `certificate_domain` to the matching issued
ACM certificate domain, apply again, and point DNS at the demo distribution.
