# Private AWS platform sandbox

This root prepares an **internal** ECS Fargate deployment of the existing mock control plane. The API image includes the built React dashboard at `/`. It creates an internal HTTPS ALB, API and worker task definitions and services, a one-shot migration task definition, scoped execution roles, security groups, and CloudWatch logs. Services start at zero tasks until the database migration succeeds. It does **not** provision applications requested through the API, expose the dashboard publicly, or turn mock approvals into production approvals.

## Required inputs

Supply these from an approved AWS sandbox before planning:

- A non-root deployment profile for the exact `aws_account_id` and an access-controlled, versioned S3 state bucket with a dedicated key and lockfile. Use a separate key from the existing network/ECR root.
- A VPC with at least two **private** ALB subnets in different Availability Zones and private task subnets. Tasks need outbound access to Temporal Cloud and to ECR, Secrets Manager, and CloudWatch Logs through reviewed NAT or VPC endpoints. The current `../aws-sandbox` module creates only one subnet and does not meet this requirement.
- Private PostgreSQL (for example RDS) with backups, a security group allowing port 5432 from the output `task_security_group_id`, and a `postgresql+psycopg://...` URL stored as a Secrets Manager secret. The URL must use TLS as required by the database configuration.
- A Temporal Cloud namespace endpoint and API key, stored in Secrets Manager. Both API and worker use TLS. Confirm outbound TCP 7233 and namespace permissions.
- A private DNS name resolving to the internal ALB and an ACM certificate for that name in the deployment Region. Restrict `allowed_ingress_cidrs` to the operator VPN or private network.
- Separate Secrets Manager values for a randomly generated dashboard bearer token and agent signing key. Never put secret values in Terraform variables, state, Git, or task environment literals. The sandbox operator email is `dashboard_requester`.
- A digest-pinned ECR image built from the repository root. The ECR repository may come from `../aws-sandbox`.

The execution role can pull only the named ECR repository, write the named log group, and read the four named secrets. The API and worker task roles have no AWS permissions. If secrets use a customer-managed KMS key, add a narrowly scoped `kms:Decrypt` grant for the execution role before launching tasks.

## Build and review

Run the repository checks and build the image on a machine with Docker:

```sh
uv sync --locked --extra test
uv run --locked --extra test pytest -q tests
opa test security/opa infrastructure/policies -v
terraform fmt -check -recursive infrastructure
docker build --platform linux/amd64 -t devops-aws-sandbox:review .
docker run --rm -e AWS_SANDBOX_MODE=0 --entrypoint python devops-aws-sandbox:review -c 'import apps.api.main; import orchestration.temporal.workers.mock_worker'
docker run --rm --entrypoint opa devops-aws-sandbox:review version
```

Push an immutable, commit-tagged image to the approved ECR repository using a scoped deployment profile. Record the returned ECR image digest and set `TF_VAR_image_uri` to `ACCOUNT.dkr.ecr.REGION.amazonaws.com/REPOSITORY@sha256:DIGEST`. Do not deploy a mutable tag.

Set `AWS_PROFILE`, `AWS_REGION`, and `TF_VAR_*` values for all required variables in `variables.tf`. Keep `api_desired_count` and `worker_desired_count` at zero. Initialize this root with its own S3 key and account guard, following the backend command pattern in [the network sandbox runbook](../aws-sandbox/README.md). Use a distinct path such as `platform-sandbox/terraform.tfstate`. Then:

```sh
terraform init -reconfigure -backend-config="bucket=APPROVED_STATE_BUCKET" \
  -backend-config="key=platform-sandbox/terraform.tfstate" \
  -backend-config="region=STATE_BUCKET_REGION" \
  -backend-config="allowed_account_ids=[\"APPROVED_STATE_ACCOUNT_ID\"]" \
  -backend-config="use_lockfile=true"
terraform validate
terraform plan -out=platform.tfplan
terraform show -json platform.tfplan > platform-plan.json
```

The saved plan and its JSON can contain sensitive values. Store them in a protected location outside Git; review resource additions, identity policy, network reachability, and cost before applying the **same saved plan**. A human operator applies the reviewed plan only with the scoped non-root profile. The current mock workflow approval token does not authorize this Terraform plan.

## Start in stages

1. Apply the reviewed plan with both desired counts at zero. Record `cluster_arn`, `migration_task_definition_arn`, and `task_security_group_id` from outputs.
2. Permit database ingress from that task security group and verify task-subnet egress. Run the migration task once using the output task definition, one of `task_subnet_ids`, the task security group, `assignPublicIp=DISABLED`, and Fargate launch type. Wait for it to stop; require container exit code **0** and inspect `/ecs/NAME` logs. Do not scale services after a failed migration.
3. Plan and review a second change with `api_desired_count=1` and `worker_desired_count=1`, then apply that saved plan. ECS deployment circuit breakers can roll back a failed service deployment.
4. From the approved private network, call `https://PRIVATE_API_NAME/health` and require HTTP 200. Open `https://PRIVATE_API_NAME/` and enter the configured dashboard token. Call `/dashboard/workflows` without a bearer token and require 403. With the token, verify the empty or expected workflow list. Check the ALB target health, ECS service events, worker logs, and Temporal namespace connectivity.
5. Submit one sandbox request and confirm it reaches `awaiting_approval`. This deployment deliberately disables the workstation mock approval issuer; completion needs a separately authenticated approver integration before shared use.

## Rollback and operations

For a bad rollout, restore the previous digest-pinned `image_uri` through a reviewed plan; ECS also has deployment circuit breakers enabled. For an incident, set both desired counts to zero through a reviewed plan. Do not roll back the database schema by deleting rows or state; restore from an approved backup procedure if required. Watch ALB unhealthy targets, ECS stopped tasks and deployment events, CloudWatch logs, RDS health, and Temporal worker poller health during the first hour. Rotate Secrets Manager values by starting new task revisions; running tasks do not automatically reload injected secrets.

This root is a private **mock pilot**. Public access, enterprise SSO, tenant authorization, a real approval issuer, saved-plan binding for application provisioning, live delivery adapters, managed alert destinations, and tested restore remain release gates.
