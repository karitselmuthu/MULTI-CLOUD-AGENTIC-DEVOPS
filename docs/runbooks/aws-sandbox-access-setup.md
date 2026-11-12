# Set up non-root access for the first AWS sandbox

The dashboard currently reports simulated delivery. A live sandbox requires a scoped human profile for the one-time state bootstrap, a platform deployment role, and separate application provisioner roles. The selected CLI profile resolved to the AWS account root principal and was logged out. Do not use it to run the sandbox.

| Access | Who uses it | Permission boundary |
| --- | --- | --- |
| `DevOpsSandboxStateBootstrap` | Human operator, briefly | Custom permission set limited to the reviewed state-bucket CloudFormation stack and its S3 bucket; MFA required. |
| `DevOpsPlatformDeployer` | Human or CI deployment process | Custom policy for the platform stack; `iam:PassRole` restricted to named platform task roles. |
| `DevOpsSandboxProvisioner` | Per-application executor | Custom policy for the approved module and reviewed plan's required AWS actions; limited to the application's resources, state key and lock object. |
| Future CI role | GitHub Actions | OIDC trust restricted to this repository and approved branch/environment; no static access keys. |

These are **separate principals**, not one user with several policies. A permission set grants a human access through IAM Identity Center; an IAM role has its own trust policy (who may assume it) and permissions policy (what it may do). The platform deployer and application provisioner are proposed roles; neither is created by the current Terraform. The current module manages only a VPC, one subnet, and an ECR repository. It does not need an EC2 instance profile or EKS service role yet.

### What each identity needs

| Identity | Trust / sign-in | Allow only | Keep outside its scope |
| --- | --- | --- | --- |
| State bootstrap operator | Named human in the Identity Center group, with MFA | Review and execute change sets for `multicloud-agentic-devops-tfstate`; create and configure the one named S3 state bucket and bucket policy, as required by the reviewed template | Application resources, general IAM role creation, all other buckets and stacks |
| Platform deployer | Separate human permission set initially; later a tightly scoped CI role | Deploy the platform's network, ECS services, load balancer, database, images and configuration; pass only the explicitly named ECS task/execution roles to ECS; access only platform state | Application provisioning and arbitrary `iam:PassRole` |
| API task role | ECS task service principal | Only API runtime needs, such as its own secrets, metadata, and artifact reads | Terraform apply, IAM role creation, and application provisioner assumption |
| Worker task role | ECS task service principal | Workflow runtime needs; `sts:AssumeRole` on an explicitly listed per-application provisioner role after the application's approval checks | Broad account-wide infrastructure permissions |
| Application provisioner | Trust only the named worker task role (or a separately approved Terraform executor) | Actions for that application's approved resource types, Region and state prefix; `iam:PassRole` only for named application roles if its module needs them | Platform state, other tenants' resources, unrestricted IAM or network changes |
| CI deployment role | GitHub OIDC provider, exact repository and approved branch or environment in the trust policy | The subset of platform deployment actions required by its workflow | Root credentials, static access keys, wildcard repository trust |

For ECS, the **task role** is used by application code; the **task execution role** is used by ECS to pull images, send logs, and retrieve configured secrets. Name and scope both before giving the platform deployer `iam:PassRole`, and constrain that action to the intended service with `iam:PassedToService` where applicable. A CloudFormation service role is optional for the state stack. If one is used, restrict it to the state resources and allow the bootstrap operator to pass only that role to CloudFormation. CloudFormation keeps using a stack's service role for later operations, so a broad service role would undermine the operator's narrow permissions. [ECS task role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html) · [ECS execution role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html) · [PassRole](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html) · [CloudFormation service role](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html).

Terraform's S3 backend needs bucket listing and object read/write access for the dedicated state key, plus the `.tflock` object when `use_lockfile=true`; the state bootstrap operator needs separate permissions to **create** the bucket. Do not give every application access to the entire state bucket. A Terraform plan identifies proposed resource changes; it does **not** produce an IAM policy. Map the reviewed resource types to required AWS API actions using the AWS service authorization references, restrict resource ARNs and supported conditions, then test the policy with the scoped non-root identity. Where an application may create IAM roles, require an approved permissions boundary. [Terraform S3 backend permissions](https://developer.hashicorp.com/terraform/language/backend/s3#permissions-required) · [AWS service authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) · [IAM permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html).

Use a distinct provisioner role and state prefix per application or tenant. If one worker can assume several such roles, the worker must enforce tenant authorization and approval before each assumption; IAM role trust alone cannot validate a Terraform plan hash. The live approval-to-assume-role path is **not implemented yet** in this repository.

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

Create separate roles for platform deployment and application provisioning. The API runtime should not hold infrastructure mutation permissions. The worker may assume only the intended per-application provisioner role after exact-plan approval. Scope each provisioner to its application, tenant, Region, and state key; apply a permissions boundary where it can create roles. Review `terraform show -json` to identify proposed resources, map those resources to documented AWS actions, then review and test the resulting policy before use. The [AWS sandbox root](../../infrastructure/environments/aws-sandbox/README.md) also guards the expected account and uses S3 locking. See [AWS resource and cost plan](../architecture/aws-resource-cost-plan.md).

For future unattended GitHub Actions runs, use a distinct OIDC-assumed role restricted to this repository and branch/environment, rather than a human SSO session or stored access keys. AWS source: [IAM security best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).
