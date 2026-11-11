# Set up non-root access for the first AWS sandbox

The dashboard currently reports simulated delivery. A live sandbox requires a human administrator profile for the one-time account bootstrap, then a separate scoped provisioner profile for routine Terraform runs. The selected CLI profile resolved to the AWS account root principal and was logged out. Do not use it to run the sandbox.

| Access | Who uses it | Permission boundary |
| --- | --- | --- |
| `DevOpsSandboxBootstrapAdmin` | Account owner, briefly | `AdministratorAccess` to establish Identity Center assignments and the protected state bucket; MFA required. |
| `DevOpsSandboxProvisioner` | Human sandbox operator | Custom policy derived from the reviewed Terraform plan; limited to the sandbox account, approved resource changes, and the state object plus lock object. |
| Future CI role | GitHub Actions | OIDC trust restricted to this repository and approved branch/environment; no static access keys. |

The current module manages only a VPC, one subnet, and an ECR repository. It does not need an EC2 instance profile or EKS service role yet. The state backend needs S3 access to the dedicated key and `.tflock` object; see the [Terraform backend permission example](https://developer.hashicorp.com/terraform/language/backend/s3#permissions-required). The exact VPC/ECR execution policy must be generated from a live plan and reviewed before attaching it.

## 1. Create the human bootstrap administrator

1. Sign in to the AWS console as the account owner for this one-time identity setup. Keep MFA enabled. Open **IAM Identity Center**. For AWS account access, use an **organization instance**; an account instance is for application assignments and does not provide the account-access flow used here. If IAM Identity Center is not enabled, follow AWS's guided setup for your account or organization.
2. In **Users**, add yourself with your real email address. Create a group named `DevOpsSandboxAdmins` and add your user. Never use the dashboard placeholder `engineer@example.com`.
3. Create a permission set named `DevOpsSandboxBootstrapAdmin`, using the AWS managed `AdministratorAccess` policy for this one-time setup. Assign that permission set and group to the intended sandbox AWS account. This grants broad administrative access, so keep the group restricted to the account owner and use it only for identity and state-bucket bootstrap.
4. Complete the invitation and enable MFA for the new Identity Center user. Sign out of the root session and use the AWS access portal as the new user. AWS creates and manages the corresponding IAM role when the account assignment is made; do not manually create an `AWSReservedSSO_*` role.

AWS sources: [administrative user quick start](https://docs.aws.amazon.com/singlesignon/latest/userguide/quick-start-default-idc.html), [account assignments](https://docs.aws.amazon.com/singlesignon/latest/userguide/manage-your-accounts.html), [Identity Center-managed roles](https://docs.aws.amazon.com/singlesignon/latest/userguide/identity-center-and-iam-roles.html), [root user best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html).

## 2. Configure and verify a short-lived CLI profile

Run `aws configure sso --profile devops-sandbox-bootstrap`. Use the access portal Start URL and **Identity Center Region** shown in the console. These may differ from the sandbox resource Region. Select the intended AWS account and `DevOpsSandboxBootstrapAdmin` role. Set the CLI default Region to `us-east-1`.

```sh
aws sso login --profile devops-sandbox-bootstrap
aws sts get-caller-identity \
  --profile devops-sandbox-bootstrap --region us-east-1
```

Confirm that `Account` is the intended sandbox account and `Arn` is an assumed role, not `...:root`. Do not copy access keys into `.env`, the repository, or Terraform variables. AWS source: [configure the CLI with IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## 3. Bootstrap protected Terraform state

Review the [prepared CloudFormation template](../../infrastructure/environments/aws-state-bootstrap/template.json) and [bootstrap notes](../../infrastructure/environments/aws-state-bootstrap/README.md). The proposed stack creates a private, versioned, encrypted S3 bucket and retains it if the stack is deleted. Review a CloudFormation change set with the bootstrap administrator, then execute that change set after confirming the bucket name, ownership tags, and scope. No stack has been created by this repository.

## 4. Use a separate routine provisioner

Create a second Identity Center permission set named `DevOpsSandboxProvisioner` and a separate CLI profile such as `devops-sandbox`. Scope its policy to the reviewed VPC, subnet, and ECR changes in the sandbox account, plus the dedicated S3 state key and its `.tflock` object. Do not attach `AdministratorAccess` to the routine provisioner. Derive the policy from a real `terraform show -json` plan once the bootstrap profile can produce one; do not guess Terraform's API actions from the `.tf` files. Review the generated policy and assignment before use. The [AWS sandbox root](../../infrastructure/environments/aws-sandbox/README.md) also guards the expected account and uses S3 locking.

For future unattended GitHub Actions runs, use a distinct OIDC-assumed role restricted to this repository and branch/environment, rather than a human SSO session or stored access keys. AWS source: [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).
