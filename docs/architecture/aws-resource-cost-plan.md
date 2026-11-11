# AWS resource and cost plan for the current project

Status: planning estimate for `us-east-1` on 2026-11-11. No AWS resources have been deployed. The existing AWS Terraform module creates only a VPC, one private subnet, and an ECR repository. It has no routes, compute, database, public endpoint, or application deployment. The local dashboard's healthy report is simulated.

## Resources needed to run the platform

| Area | First connected sandbox | Scale or production option |
| --- | --- | --- |
| Network | VPC, at least two subnets, route tables, security groups, egress through NAT or reviewed VPC endpoints | Multi-AZ routing and isolation |
| Container images | ECR for API and worker images | Separate application repositories and retention policies |
| API and worker | Two ECS Fargate services for the FastAPI control plane and Temporal worker | EKS services if the roadmap's Kubernetes target is required |
| Workflow server | Temporal Cloud connection or a separately operated production Temporal server | Highly available Temporal deployment |
| Metadata | RDS PostgreSQL, private and encrypted, with backups | Multi-AZ RDS and tested restore |
| Dashboard | Built React files in private S3 behind CloudFront; authenticated API route | Enterprise SSO and WAF as required |
| Traffic | Application Load Balancer for the API, TLS certificate and DNS | Multi-AZ target groups and regional failover |
| Artifacts and state | S3 artifact bucket plus separate versioned, locked Terraform state bucket | Per-tenant state keys and retention controls |
| Secrets and audit | Secrets Manager, CloudWatch logs, CloudTrail, budget alarm | KMS controls, tracing, SIEM export |
| Identity | Separate platform deployer, API task, worker task, and per-application provisioner roles | Cross-account tenant roles and permissions boundaries |

The current code lacks production authentication, a production Temporal deployment, and a live Terraform plan/apply path. A public deployment must close those gaps. The local dashboard token and mock approval button are not suitable for a public AWS endpoint.

## Approximate monthly costs

Assumptions: Linux/x86 on-demand pricing in `us-east-1`, 730 hours per month, low traffic, no free-tier credits, two always-on Fargate tasks of 0.5 vCPU/1 GB each, one ALB, one NAT gateway, and one small Single-AZ PostgreSQL instance. These are planning allowances, not a quote; use the [AWS Pricing Calculator](https://calculator.aws/) with the final architecture before deployment.

| Item | Monthly possibility | Basis |
| --- | ---: | --- |
| API and worker Fargate tasks | about **$36** | Two 0.5-vCPU/1-GB tasks, 730 hours; [Fargate rate example](https://aws.amazon.com/fargate/pricing/) |
| Application Load Balancer | **$16.43 base**, about **$22** with one LCU | [ALB rates](https://aws.amazon.com/elasticloadbalancing/pricing/) |
| One NAT gateway | about **$33** plus data processing | Illustrative $0.045/hour from AWS's US East (Ohio) example; confirm the `us-east-1` rate in the calculator before deployment; [VPC pricing](https://aws.amazon.com/vpc/pricing/) |
| RDS PostgreSQL | budget **$20–$50+** | Instance, storage, backups, and possible CPU credits vary; [RDS pricing](https://aws.amazon.com/rds/postgresql/pricing/) |
| Public IPv4 | **$3.65 per address** | $0.005/hour; [VPC pricing](https://aws.amazon.com/vpc/pricing/) |
| Secrets, logs, S3, ECR, CloudFront | budget **$5–$25+** at low usage | Usage-based; [Secrets](https://aws.amazon.com/secrets-manager/pricing/), [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/), [S3](https://aws.amazon.com/s3/pricing/), [ECR](https://aws.amazon.com/ecr/pricing/), [CloudFront](https://aws.amazon.com/cloudfront/pricing/) |
| EKS control plane, if selected | add **$73** per cluster during standard support | $0.10/hour, worker compute extra; [EKS pricing](https://aws.amazon.com/eks/pricing/) |
| Self-hosted single Temporal server task, if selected | add about **$36** compute, plus database/operations | Illustrative 1-vCPU/2-GB Fargate task; not a highly available Temporal deployment |

The **ECS + Temporal Cloud** pilot is roughly **$120–$200/month in AWS** under these assumptions, plus Temporal Cloud usage and internet data transfer. This is a planning range, not a validated `us-east-1` quote. Temporal Cloud currently lists no base monthly fee and consumption charges for actions and storage; [Temporal pricing](https://temporal.io/pricing). Self-hosting Temporal or using EKS raises the fixed cost. A production Multi-AZ design, WAF, more logs, and larger RDS can cost substantially more.

## Incremental cost for each application the platform builds

The application request must specify whether it shares the platform VPC, ALB, and cluster. A continuously running small Fargate task costs about **$9/month** at 0.25 vCPU/0.5 GB or **$18/month** at 0.5 vCPU/1 GB, before logs, image storage, traffic, and databases. A dedicated ALB adds its own hourly and LCU charges; a dedicated NAT gateway adds about **$33/month** plus traffic. A dedicated EKS cluster adds the **$73/month** control-plane charge before nodes. A per-app RDS database is another material line item. These figures follow the same [Fargate](https://aws.amazon.com/fargate/pricing/), [ALB](https://aws.amazon.com/elasticloadbalancing/pricing/), [VPC](https://aws.amazon.com/vpc/pricing/), and [EKS](https://aws.amazon.com/eks/pricing/) rate assumptions above.

Each app also needs an approved module, isolated state, cost-center tags, a scoped execution role, budget limits, and a real deployment target. The present `sandbox-api` module provisions only network and ECR resources; it does not create or run an application.
