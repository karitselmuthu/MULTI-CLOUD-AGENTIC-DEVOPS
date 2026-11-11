# AWS sandbox root

This root connects the existing approved AWS module to one explicitly selected AWS account. It creates only a VPC, a private subnet, and an ECR repository. It does not deploy an application, EKS cluster, or image. Review the proposed VPC/subnet CIDRs against existing networks before any live plan.

The AWS provider checks `aws_account_id` with `allowed_account_ids`. Terraform state must use an existing, access-controlled S3 bucket with bucket versioning and `use_lockfile=true`; this repository does not create that bucket. The bucket and state key should be dedicated to this sandbox. Never put access keys in Terraform files or `-backend-config`; use a short-lived AWS profile. [AWS provider account guard](https://registry.terraform.io/providers/hashicorp/aws/latest/docs#allowed_account_ids) · [S3 backend and locking](https://developer.hashicorp.com/terraform/language/backend/s3).

Once the account owner supplies the profile, account ID, region, state bucket, state key, CIDRs, availability zone, owner, and cost center, run the read-only preflight from the repository root. It verifies the STS account, rejects root credentials, confirms the zone is available, and checks the subnet lies inside the VPC:

```sh
uv run --locked python -m apps.cli.aws_preflight \
  --profile PROFILE --account-id APPROVED_12_DIGIT_ACCOUNT_ID \
  --region REGION --availability-zone APPROVED_AZ \
  --vpc-cidr APPROVED_VPC_CIDR --subnet-cidr APPROVED_SUBNET_CIDR
```

Authenticate with the organization's established short-lived credential flow if the session has expired.

Initialize state with the approved bucket. The backend's account guard protects state access independently of the provider guard:

```sh
cd infrastructure/environments/aws-sandbox
export AWS_PROFILE=PROFILE
export AWS_REGION=REGION
export TF_VAR_aws_account_id=APPROVED_12_DIGIT_ACCOUNT_ID
export TF_VAR_aws_region=REGION
export TF_VAR_name=UNIQUE_SANDBOX_PREFIX
export TF_VAR_vpc_cidr=APPROVED_VPC_CIDR
export TF_VAR_subnet_cidr=APPROVED_SUBNET_CIDR
export TF_VAR_availability_zone=APPROVED_AZ
export TF_VAR_owner=OWNER_TAG
export TF_VAR_cost_center=COST_CENTER_TAG

terraform init -reconfigure \
  -backend-config="bucket=EXISTING_STATE_BUCKET" \
  -backend-config="key=APPROVED_UNIQUE_KEY/terraform.tfstate" \
  -backend-config="region=STATE_BUCKET_REGION" \
  -backend-config="allowed_account_ids=[\"APPROVED_STATE_ACCOUNT_ID\"]" \
  -backend-config="use_lockfile=true"
```

The first connected step is a **saved plan and policy review**, not an apply. The current dashboard approval token is bound to the **mock** plan digest, so it cannot authorize a real Terraform plan. A live executor must hash the exact saved binary plan, validate its JSON against policy, obtain an approval bound to that digest, and apply that same file. Saved plans can contain sensitive data; keep them outside Git and restrict access. [Terraform saved plan](https://developer.hashicorp.com/terraform/cli/commands/plan#out-filename) · [Applying a saved plan](https://developer.hashicorp.com/terraform/cli/commands/apply#saved-plan-mode).
