# Set up non-root access for the first AWS sandbox

The dashboard currently reports simulated delivery. A live sandbox requires a scoped human profile for the one-time state bootstrap, a platform deployment role, and separate application provisioner roles. The selected CLI profile resolved to the AWS account root principal and was logged out. Do not use it to run the sandbox.

| Access | Who uses it | Permission boundary |
| --- | --- | --- |
| `DevOpsSandboxStateBootstrap` | Human operator, briefly | Custom permission set limited to the reviewed state-bucket CloudFormation stack and its S3 bucket; MFA required. |
| `DevOpsPlatformDeployer` | Human or CI deployment process | Custom policy for the platform stack; `iam:PassRole` restricted to named platform task roles. |
| `DevOpsSandboxProvisioner` | Per-application executor | Custom policy derived from each reviewed Terraform plan; limited to approved modules, application scope, and its state key and lock object. |
| Future CI role | GitHub Actions | OIDC trust restricted to this repository and approved branch/environment; no static access keys. |

The current module manages only a VPC, one subnet, and an ECR repository. It does not need an EC2 instance profile or EKS service role yet. The state backend needs S3 access to the dedicated key and `.tflock` object; see the [Terraform backend permission example](https://developer.hashicorp.com/terraform/language/backend/s3#permissions-required). The exact VPC/ECR execution policy must be generated from a live plan and reviewed before attaching it.

## 1. Create the scoped human bootstrap operator

1. Sign in to the AWS console as the account owner for this one-time identity setup. Keep MFA enabled. Open **IAM Identity Center**. For AWS account access, use an **organization instance**; an account instance is for application assignments and does not provide the account-access flow used here. If IAM Identity Center is not enabled, follow AWS's guided setup for your account or organization.
2. In **Users**, add yourself with your real email address. Create a group named `DevOpsSandboxOperators` and add your user. Never use the dashboard placeholder `engineer@example.com`.
3. Create a **custom** permission set named `DevOpsSandboxStateBootstrap`. Limit it to the prepared state-bucket stack and bucket, with only the CloudFormation, S3, and read-only calls required for that bootstrap. Do not attach `AdministratorAccess` or `PowerUserAccess`. Review the exact policy against the template and AWS service authorization reference before assigning it. The account owner may need to perform the initial Identity Center configuration; use that access only for the bootstrap.
4. Complete the invitation and enable MFA for the new Identity Center user. Sign out of the root session and use the AWS access portal as the new user. AWS creates and manages the corresponding IAM role when the account assignment is made; do not manually create an `AWSReservedSSO_*` role.

AWS sources: [administrative user quick start](https://docs.aws.amazon.com/singlesignon/latest/userguide/quick-start-default-idc.html), [account assignments](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-accounts.html), [Identity Center-managed roles](https://docs.aws.amazon.com/singlesignon/latest/userguide/identity-center-and-iam-roles.html), [root user best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html).

## 2. Configure and verify a short-lived CLI profile

Run `aws configure sso --profile devops-sandbox-bootstrap`. Use the access portal Start URL and **Identity Center Region** shown in the console. These may differ from the sandbox resource Region. Select the intended AWS account and `DevOpsSandboxStateBootstrap` role. Set the CLI default Region to `us-east-1`.

```sh
aws sso login --profile devops-sandbox-bootstrap
aws sts get-caller-identity \
  --profile devops-sandbox-bootstrap --region us-east-1
```

Confirm that `Account` is the intended sandbox account and `Arn` is an assumed role, not `...:root`. Do not copy access keys into `.env`, the repository, or Terraform variables. AWS source: [configure the CLI with IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## 3. Bootstrap protected Terraform state

Review the [prepared CloudFormation template](../../infrastructure/environments/aws-state-bootstrap/template.json) and [bootstrap notes](../../infrastructure/environments/aws-state-bootstrap/README.md). The proposed stack creates a private, versioned, encrypted S3 bucket and retains it if the stack is deleted. Review a CloudFormation change set with the scoped bootstrap operator, then execute that change set after confirming the bucket name, ownership tags, and scope. No stack has been created by this repository.

## 4. Use a separate routine provisioner

Create separate roles for platform deployment and application provisioning. The API runtime should not hold infrastructure mutation permissions. The worker may assume only the intended per-application provisioner role after exact-plan approval. Scope each provisioner to its application, tenant, Region, and state key; apply a permissions boundary where it can create roles. Derive the execution policy from a real `terraform show -json` plan once a scoped profile can produce one; do not guess Terraform's API actions from the `.tf` files. Review the generated policy and assignment before use. The [AWS sandbox root](../../infrastructure/environments/aws-sandbox/README.md) also guards the expected account and uses S3 locking. See [AWS resource and cost plan](../architecture/aws-resource-cost-plan.md).

For future unattended GitHub Actions runs, use a distinct OIDC-assumed role restricted to this repository and branch/environment, rather than a human SSO session or stored access keys. AWS source: [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).
