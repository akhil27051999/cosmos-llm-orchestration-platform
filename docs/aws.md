# Module 8: AWS — Deploying This Project to the Cloud

> **Goal:** Know exactly which AWS services this project would use, **why** each one is needed, and **how** to wire them up — deeply enough to explain the architecture in an interview and actually build it when you want to.
>
> **Scope:** Only the services you'd actually touch to run this project on AWS. No encyclopedic surveys. Each section maps 1:1 to something you already built locally (minikube → EKS, Vault → Secrets Manager, DockerHub → ECR, and so on).

---

## How to Read This Doc

Each service section follows the same structure so you can drill on it:

1. **What it is** — plain explanation, no marketing.
2. **Your project today uses X; on AWS you'd use this.** — the concrete swap.
3. **Key concepts you must know** — the ~5 ideas an interviewer will probe.
4. **How you'd implement it for this project** — actual Terraform / YAML you'd add.
5. **Gotchas** — the traps that trip people up.
6. **Interview Q&A** — questions you should be able to answer cold.

---

## Table of Contents

1. [Overview — Your Project on AWS in One Picture](#overview--your-project-on-aws-in-one-picture)
2. [Service 1: VPC + Networking](#service-1-vpc--networking) — the base layer (you already have this)
3. [Service 2: EKS](#service-2-eks) — replaces minikube
4. [Service 3: ECR](#service-3-ecr) — replaces DockerHub
5. [Service 4: RDS for PostgreSQL](#service-4-rds-for-postgresql) — replaces in-cluster Postgres
6. [Service 5: IAM + IRSA](#service-5-iam--irsa) — how pods get AWS permissions
7. [Service 6: Secrets Manager](#service-6-secrets-manager) — replaces Vault (optional)
8. [Service 7: ALB + Route 53 + ACM](#service-7-alb--route-53--acm) — public entry point
9. [Service 8: S3](#service-8-s3) — Terraform state + backups
10. [Service 9: CloudWatch + AMP/AMG](#service-9-cloudwatch--ampamg) — observability on AWS
11. [Service 10: KMS](#service-10-kms) — the encryption thread
12. [Service 11: AWS CI/CD (CodePipeline / CodeBuild / CodeDeploy)](#service-11-aws-cicd) — the native alternative to GitHub Actions
13. [End-to-End Architecture](#end-to-end-architecture)
14. [90-Day Implementation Roadmap](#90-day-implementation-roadmap)
15. [Cost Estimate](#cost-estimate)

---

## Overview — Your Project on AWS in One Picture

Your minikube stack maps to AWS like this:

| What you have locally | AWS service | Why swap |
|---|---|---|
| Minikube 3-node cluster | **EKS** | Managed control plane, real multi-AZ |
| DockerHub | **ECR** | Same VPC as cluster (fast pulls), IAM-auth, scanning |
| Postgres Deployment in K8s | **RDS for PostgreSQL** | Managed backups, Multi-AZ failover, no statefulset pain |
| Vault + ESO | **AWS Secrets Manager + ESO** | Rotation, IAM-integrated, one less thing to run |
| Minikube nginx Ingress | **ALB via AWS Load Balancer Controller** | Managed, public, WAF-ready |
| `/etc/hosts` / minikube tunnel | **Route 53** (DNS) + **ACM** (TLS) | Real domain + auto-renewing certs |
| Local tfstate | **S3 + DynamoDB lock** | Team-safe, versioned, recoverable |
| Prometheus/Grafana/Loki | Keep **OSS on EKS**, or use **AMP + AMG** | Less ops if you pick managed |
| K8s Secrets | **KMS-encrypted** | Compliance + audit |

Cluster networking lives inside the **VPC** you already defined in `terraform/main.tf` — that part doesn't change, it's the foundation for everything above.

**Diagram of the target:**

```
                             ┌──────────────────┐
                             │   Route 53       │  user hits api.example.com
                             │ api.example.com  │
                             └────────┬─────────┘
                                      │
                                      ▼
                             ┌────────────────────┐
                             │   ACM cert (443)   │
                             └────────┬───────────┘
                                      │
┌─── VPC 10.0.0.0/16 ──────────────────────────────────────────────────────┐
│                                                                          │
│  PUBLIC  10.0.0.0/24 (az-a)     PUBLIC  10.0.10.0/24 (az-b)              │
│  ┌─────────┐ ┌──────┐           ┌─────────┐ ┌──────┐                     │
│  │  ALB    │ │ NAT  │           │  ALB    │ │ NAT  │                     │
│  │ (443)   │ │  GW  │           │ (443)   │ │  GW  │                     │
│  └────┬────┘ └──────┘           └────┬────┘ └──────┘                     │
│       │                              │                                   │
│       ▼                              ▼                                   │
│  APP  10.0.1.0/24 (az-a)       APP  10.0.11.0/24 (az-b)                  │
│  ┌───────────────┐             ┌───────────────┐                         │
│  │ EKS nodes     │             │ EKS nodes     │                         │
│  │ (Karpenter)   │             │ (Karpenter)   │                         │
│  │   ┌─────┐     │             │   ┌─────┐     │                         │
│  │   │pod  │───┐ │             │   │pod  │───┐ │                         │
│  │   └─────┘   │ │             │   └─────┘   │ │                         │
│  │             │ │             │             │ │                         │
│  └─────────────┼─┘             └─────────────┼─┘                         │
│                │                             │                           │
│          IRSA-scoped calls                   │                           │
│                ▼                             ▼                           │
│         Secrets Manager       S3         RDS Postgres (writer in az-a)   │
│         (DB password)       (backups)    ┌──────────────────────────┐    │
│         ECR (image pull)                 │  synchronous standby az-b│    │
│                                          └──────────────────────────┘    │
│                                                                          │
│  DB  10.0.2.0/24 (az-a)    DB  10.0.12.0/24 (az-b) — RDS subnet group    │
└──────────────────────────────────────────────────────────────────────────┘
```

Everything below explains how to get there.

---

## Service 1: VPC + Networking

### What it is

A **VPC** is a logically isolated virtual network in AWS — your own IP range, your own routing tables, your own firewalls. Everything else (EKS, RDS, ALB) lives inside subnets of this VPC.

### Your project today uses this; on AWS you'd use this

You already have `terraform/main.tf` that defines:

- VPC `10.0.0.0/16`
- 5-tier subnets per AZ: **public / app / db / dependent / observability**
- 2 AZs (`us-east-1a`, `us-east-1b`)
- Internet Gateway + NAT Gateway per AZ
- 6 Security Groups (alb / app / db / dependent / observability / api_server)

You **don't need to add anything** — this is the foundation. What changes is what sits **in** the subnets.

### Key concepts you must know

**1. Subnet = AZ + CIDR + route table association.**
A subnet is "private" or "public" only because of its route table:
- Public → has `0.0.0.0/0 → IGW` route. Resources can have public IPs.
- Private → has `0.0.0.0/0 → NAT GW` route. Outbound only.
- Isolated (your `db` subnet) → no `0.0.0.0/0` route at all.

**2. Security Group vs NACL.**

| | **Security Group** | **NACL** |
|---|---|---|
| Attached to | An ENI (instance, pod, RDS, ALB) | A whole subnet |
| Stateful? | **Yes** — return traffic auto-allowed | No — rules for both directions |
| Rules | Allow only | Allow + Deny |
| Reference other? | **Other SG IDs** (big deal) | CIDR only |

SG tier pattern (which you already implement):
```
alb_sg  : inbound 443 from 0.0.0.0/0
app_sg  : inbound 8080 from alb_sg     ← references SG, not IP
db_sg   : inbound 5432 from app_sg
```
This means scaling out app instances Just Works — new ENI is in `app_sg`, DB trusts it automatically.

**3. NAT Gateway is per-AZ for high availability.**
Your Terraform does this right (`for_each = var.azs` on `aws_nat_gateway.main`). If AZ-a dies, subnets in AZ-b still egress through their own NAT. Don't put all subnets behind one NAT in one AZ — that's a single point of failure **and** inter-AZ traffic costs.

**4. VPC Endpoints.**
Traffic from a private subnet to S3/ECR/KMS would otherwise go out NAT → internet → back to AWS. Expensive and slow. **Add these endpoints:**

| Endpoint | Type | What it fixes |
|----------|------|---------------|
| S3 | Gateway (free) | Image layer pulls, backups, CI artifacts |
| DynamoDB | Gateway (free) | — (not used by this project) |
| ECR API + ECR DKR | Interface (paid) | Docker image pulls by nodes |
| Secrets Manager | Interface (paid) | ESO / app fetching secrets |
| STS | Interface (paid) | IRSA token exchange |
| Logs (CloudWatch) | Interface (paid) | Log shipping |

Without endpoints, each pod pulling an image round-trips the public internet → NAT charges. With S3 gateway + ECR endpoints, image pulls stay on AWS backbone.

**5. CIDR sizing.**
Your `/24` (256 IPs, 251 usable) is fine for ~200 pods per AZ. With VPC CNI (default on EKS), **every pod gets a VPC IP** — so small subnets run out of IPs during scale-up. Plan `/20` or `/19` for app subnets if you expect >1000 pods.

### How you'd implement it for this project

You're mostly done. To finish the production version, add VPC endpoints to `terraform/main.tf`:

```hcl
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [
    aws_route_table.private.id,
    aws_route_table.private_db.id,
  ]
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for s in aws_subnet.app_private : s.id]
  security_group_ids  = [aws_security_group.app_sg.id]
  private_dns_enabled = true
}
# repeat for ecr.dkr, secretsmanager, sts, logs
```

Enable **VPC Flow Logs** to S3 so you can debug connectivity (SG/NACL rejections appear as `ACTION=REJECT`):

```hcl
resource "aws_flow_log" "vpc" {
  log_destination      = aws_s3_bucket.flow_logs.arn
  log_destination_type = "s3"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
}
```

### Gotchas

- **`for_each` vs `count` for subnets.** You're using `for_each` over a map — good. If you remove `us-east-1a` from the map later, only those subnets are destroyed. With `count`, removing index 0 would destroy + recreate ALL subsequent subnets because indices shift.
- **5 reserved IPs per subnet** (`.0` network, `.1` VPC router, `.2` DNS, `.3` future, `.255` broadcast). `/24` = 251 usable, not 256.
- **Changing CIDRs is hard.** You can add a secondary CIDR block, but changing the primary requires recreating the VPC. Size up generously on day 1.
- **Default SG accepts all traffic within itself.** Don't use the default SG for anything — create tier-specific SGs like you already did.
- **No transitive peering.** If VPC A peers VPC B and VPC B peers VPC C, A cannot reach C. Use Transit Gateway for hub-and-spoke.

### Interview Q&A

1. **Public vs private subnet — what's the actual difference?**
   > Whether the route table has `0.0.0.0/0 → IGW`. Nothing else. There's no "public" flag on a subnet.

2. **Why is NAT Gateway per-AZ?**
   > It's a zonal resource. If the only NAT is in us-east-1a and that AZ fails, all private subnets lose egress. One NAT per AZ, each route table points to its own-AZ NAT.

3. **Your DB subnet has no internet route. How does Postgres get OS patches?**
   > RDS is managed — AWS patches it via the service's own network, not yours. For self-managed DBs on EC2 you'd need NAT; for RDS you don't.

4. **SG vs NACL — when each?**
   > SGs for 99% of daily traffic control (stateful, SG-referencing). NACLs for subnet-wide deny rules (block a specific IP range, defense in depth). Never try to do per-instance control with NACLs.

5. **You see a $2k NAT bill. How do you debug?**
   > CloudWatch metrics on the NAT GW → `BytesOutToDestination`. Enable VPC Flow Logs → query in Athena for top talkers. Usually S3 or ECR pulls. Fix: VPC endpoints.

---

## Service 2: EKS

### What it is

**Elastic Kubernetes Service** — AWS runs the Kubernetes **control plane** (API server, etcd, scheduler, controller-manager). You run the **worker nodes** (EC2 instances or Fargate tasks) that host your pods.

### Your project today uses minikube; on AWS you'd use EKS

Minikube runs a single-node (or multi-node, in your case) cluster on your Mac using Docker as the hypervisor. EKS gives you the same Kubernetes API you already use, but:

- Control plane is HA across 3 AZs, managed by AWS.
- Workers are EC2 instances in your VPC subnets.
- Pod IPs come from the VPC CIDR directly (VPC CNI plugin) — no overlay network.
- Your **Helm charts and ArgoCD setup work as-is**.

### Key concepts you must know

**1. Control plane vs data plane.**
- Control plane: AWS-managed, you only pay `$0.10/hr` per cluster (~$73/mo).
- Data plane: your EC2 nodes (or Fargate). You pick the instance types + quantity.

**2. Node groups — three ways to run workers:**

| Option | How | Use |
|--------|-----|-----|
| **Managed node groups** | AWS-managed ASG of EC2 | Default choice; easy upgrades |
| **Self-managed nodes** | You build AMI + ASG yourself | Max customization; rarely needed |
| **Fargate profiles** | AWS runs each pod in its own tiny VM | No nodes to manage; no DaemonSets; slower starts |
| **Karpenter** | Open-source node autoscaler that provisions EC2 directly | **Best-in-class** — picks optimal instance type per pod, spins up in seconds |

**Recommendation for your project:** 1 managed node group (2× `t3.medium` baseline) + **Karpenter** for everything else. Karpenter replaces Cluster Autoscaler and is faster + cheaper (it right-sizes instance picks).

**3. VPC CNI — the networking model.**
Each pod gets a **VPC IP** (secondary IP on a node's ENI). No overlay. This means:
- Pod IPs are routable from anywhere in the VPC.
- SGs can target pods directly (via `aws-vpc-cni` + security groups for pods feature).
- **ENI limits per instance type** cap pod density. `t3.medium` → ~17 pods. Enable **prefix delegation** (`WARM_PREFIX_TARGET=1`) to scale to ~110 pods on the same instance.

**4. Cluster auth — aws-auth ConfigMap (legacy) + Access Entries (new).**
To give humans or roles `kubectl` access, map their IAM ARN to a K8s group. Newer method: **EKS Access Entries** (2024+), replaces `aws-auth` ConfigMap fumbling.

**5. Add-ons you'll install (AWS Load Balancer Controller, EBS CSI, etc.)** — EKS lets you install these as "EKS Add-ons" (versioned, managed upgrades) instead of raw Helm charts. Prefer add-ons when available.

### How you'd implement it for this project

**Minimum EKS setup in Terraform** (uses the official `terraform-aws-modules/eks` module — writing raw resources is painful):

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project_name}-eks"
  cluster_version = "1.31"

  vpc_id     = aws_vpc.main.id
  subnet_ids = [for s in aws_subnet.app_private : s.id]

  enable_irsa                              = true   # we'll use this for ESO, ALB controller, etc.
  cluster_endpoint_public_access           = true
  cluster_endpoint_public_access_cidrs     = ["YOUR_OFFICE_IP/32"]

  # One small managed node group for system workloads
  eks_managed_node_groups = {
    system = {
      min_size     = 2
      max_size     = 4
      desired_size = 2
      instance_types = ["t3.medium"]
      labels = { "workload-type" = "system" }
    }
  }

  cluster_addons = {
    vpc-cni                = { most_recent = true }
    coredns                = { most_recent = true }
    kube-proxy             = { most_recent = true }
    aws-ebs-csi-driver     = { most_recent = true }
  }
}
```

Then install Karpenter for everything else, and your existing Helm charts (`helm/application`, `helm/database`, `helm/vault`, `helm/prometheus`, ...) all apply unchanged.

**Node labels** to preserve your minikube pattern (`type=application/database/dependent_services/observability`):

```hcl
eks_managed_node_groups = {
  application = {
    labels = { type = "application" }
    taints = [{ key = "type", value = "application", effect = "NO_SCHEDULE" }]
  }
  database = {
    labels = { type = "database" }
    taints = [{ key = "type", value = "database", effect = "NO_SCHEDULE" }]
  }
  # ...
}
```

Your Helm charts' `nodeSelector: { type: application }` keeps working.

**Ingress via ALB Controller** (see Service 7) — your existing Ingress manifests just need an annotation added.

### Gotchas

- **"Insufficient pods" on a node** — you hit the ENI IP limit. Enable VPC CNI prefix delegation. `WARM_PREFIX_TARGET=1` and `ENABLE_PREFIX_DELEGATION=true`.
- **VPC CNI uses node's SG by default.** To give pods their own SGs, enable the "security groups for pods" feature (needs specific instance types).
- **K8s version upgrades** — EKS supports N and N-1 (and N-2 for extended support, paid). Plan upgrades quarterly.
- **EBS PVCs are zonal.** A pod using an EBS PVC in us-east-1a cannot reschedule to a node in us-east-1b. Use `volumeBindingMode: WaitForFirstConsumer` in the StorageClass so PVC provisions in the same AZ the pod lands on.
- **Loadbalancer-per-Service explosion.** If each `Service: LoadBalancer` creates its own NLB, costs balloon. Use ALB Controller with `ingress.class: alb` and group ingresses by host — one ALB for many apps.
- **Pods lose pod-to-pod connectivity** when VPC CNI's warm-IP pool runs out during scale-up. Pre-provision with `WARM_IP_TARGET` or use prefix delegation.

### Interview Q&A

1. **EKS vs self-managed K8s on EC2 — tradeoffs?**
   > EKS: AWS runs control plane (HA, patches, etcd backups). You manage data plane. Self-managed: full control, more work. 99% of teams pick EKS because control plane management is the least interesting part of Kubernetes.

2. **How does a pod get a VPC IP?**
   > The VPC CNI daemon on each node grabs secondary IPs on the node's ENI from the subnet's IP pool. Pods get one of those IPs. Pod packets route natively within the VPC — no VXLAN overlay.

3. **Your cluster is full and scale-up is slow. What do you look at?**
   > (a) Cluster Autoscaler / Karpenter logs — why isn't it adding nodes? (b) EC2 instance launch time (AMI pulls, user-data scripts). (c) Pod startup time (image pull via VPC endpoint? container init?). Karpenter fixes most of this — launches in 30-60s, picks right-sized instance.

4. **Explain IRSA.**
   > IAM Roles for Service Accounts. EKS exposes an OIDC provider. You create an IAM role whose trust policy references that OIDC URL + a specific Kubernetes ServiceAccount name. Annotate the SA with the role ARN. The pod's projected token is exchanged via `sts:AssumeRoleWithWebIdentity` → temp AWS creds. No static keys.

5. **A Service of type LoadBalancer vs Ingress in EKS — which creates what?**
   > With AWS Load Balancer Controller installed: `Service: LoadBalancer` → NLB. `Ingress` → ALB. Without the controller: legacy in-tree creates CLB/NLB. Prefer Ingress + ALB for HTTP workloads.

---

## Service 3: ECR

### What it is

**Elastic Container Registry** — AWS's private Docker image registry. Like DockerHub, but inside your AWS account.

### Your project today uses DockerHub; on AWS you'd use ECR

Your CI pushes to `docker.io/<you>/flask-app:<sha>` right now. The swap is:
- Repository: `<acct>.dkr.ecr.us-east-1.amazonaws.com/flask-app`
- Auth: **IAM**, not a DockerHub username/password. Your CI uses OIDC → assumes a role → `docker login` via `aws ecr get-login-password`.
- Nodes pull via the node's IAM role + (optionally) the `ecr.api`/`ecr.dkr` VPC endpoints → no NAT bill, fast pulls.

### Key concepts you must know

**1. One repo per image name.**
You'd create `flask-app` (and later maybe `postgres-init`, etc.). Each repo can hold many tags.

**2. Lifecycle policies.**
Without a lifecycle policy, you pay to store every commit SHA forever. Typical policy: keep last 30 tagged images, expire untagged after 7 days.

```json
{
  "rules": [{
    "rulePriority": 1,
    "selection": {
      "tagStatus": "any",
      "countType": "imageCountMoreThan",
      "countNumber": 30
    },
    "action": { "type": "expire" }
  }]
}
```

**3. Image scanning.**
- **Basic** (free) — Clair-based CVE scan on push.
- **Enhanced** (paid) — Inspector-powered, continuous rescans, deeper coverage.

Both fail CI if you gate `aws ecr describe-image-scan-findings` → severity filter.

**4. Pull-through cache.**
ECR can mirror DockerHub / quay.io / k8s.gcr.io on demand. You pull `<acct>.dkr.ecr.us-east-1.amazonaws.com/docker-hub/library/postgres:15` → ECR fetches + caches + scans. Get DockerHub rate-limit relief + scanning on third-party images.

**5. Cross-region / cross-account replication.**
ECR can replicate images to another region for DR or another account for shared-services patterns.

### How you'd implement it for this project

**Terraform:**

```hcl
resource "aws_ecr_repository" "flask_app" {
  name                 = "flask-app"
  image_tag_mutability = "IMMUTABLE"   # you use SHA tags — make them uneditable
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }  # or KMS for CMK
}

resource "aws_ecr_lifecycle_policy" "flask_app" {
  repository = aws_ecr_repository.flask_app.name
  policy = jsonencode({
    rules = [
      { rulePriority = 1, selection = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }, action = { type = "expire" } }
    ]
  })
}
```

**Update your `.github/workflows/ci-pipeline.yaml`** to push to ECR via OIDC:

```yaml
permissions:
  id-token: write        # OIDC
  contents: read

jobs:
  build:
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<acct>:role/github-actions-ecr-push
          aws-region: us-east-1

      - uses: aws-actions/amazon-ecr-login@v2
        id: ecr

      - run: |
          IMAGE=${{ steps.ecr.outputs.registry }}/flask-app:${GITHUB_SHA::7}
          docker build -t $IMAGE .
          docker push $IMAGE
```

**IAM role for GitHub Actions OIDC:**

```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "github_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:akhil27051999/Flask-REST-API:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_ecr" {
  name               = "github-actions-ecr-push"
  assume_role_policy = data.aws_iam_policy_document.github_trust.json
}
```

Result: **no long-lived AWS keys** in GitHub Secrets — huge security upgrade.

### Gotchas

- **`image_tag_mutability = "MUTABLE"` is the default.** With mutable tags, someone could re-push `flask-app:abc1234` pointing to a different image. With IMMUTABLE, your SHA-tagged deploys are provably the image you built.
- **ECR auth tokens last 12 hours.** `docker login` reauths needed for long-running agents (the GH Action handles this, but your local dev setup can trip on it).
- **Private subnets with no VPC endpoint pay NAT for every layer pull.** Always add `ecr.api` + `ecr.dkr` + `s3` (layer storage) endpoints.
- **Cross-account pulls need a repository policy**, not just IAM on the puller.
- **Lifecycle policy only deletes; it doesn't notify.** If you rely on tags, don't let lifecycle nuke them unexpectedly — scope by tag prefix if needed.

### Interview Q&A

1. **Why pick ECR over DockerHub for an EKS workload?**
   > Same VPC = sub-second pulls. IAM-based auth (no static registry creds). Scanning on push. No rate limits. Logs to CloudTrail.

2. **What does the pull flow look like on EKS?**
   > Pod scheduled → kubelet calls container runtime → runtime uses node's IAM role (via IMDS) → `aws ecr get-authorization-token` → pull image over ECR interface endpoint → cached on node.

3. **How do you keep ECR clean?**
   > Lifecycle policies. Typical: keep last 30 tagged, expire untagged after 7 days. Without this, repos balloon to hundreds of GB fast in a CI-driven workflow.

4. **You need to share an image with another AWS account. How?**
   > Add a **repository policy** granting `ecr:BatchGetImage` + `ecr:GetDownloadUrlForLayer` to the other account's principal. Or use **replication** for read-heavy cross-account patterns.

5. **Immutable vs mutable tags — which should your CI use, and why?**
   > Immutable. CI tags by commit SHA, which is inherently unique. Immutability guarantees a given tag always points to the same image — if you roll back to `abc1234`, you get the exact image you tested. Mutable tags are a supply-chain risk.

---

## Service 4: RDS for PostgreSQL

### What it is

**Relational Database Service** — a managed Postgres instance. AWS handles installs, patches, backups, failover, major version upgrades (opt-in). You get a connection endpoint.

### Your project today uses Postgres-in-K8s; on AWS you'd use RDS

Your `helm/database` chart runs Postgres as a Kubernetes Deployment with a PVC. On AWS, you'd move it to **RDS** (or Aurora) and point your Flask app at the RDS endpoint. The chart goes away; the `postgres-secret` still holds `host/port/user/password`.

### Key concepts you must know

**1. Single-AZ vs Multi-AZ vs Multi-AZ DB Cluster.**

| Mode | Standby | Failover time | Readable standby? | Cost |
|------|---------|---------------|---------------------|------|
| Single-AZ | None | N/A (manual restore) | — | Cheapest |
| **Multi-AZ (classic)** | Sync standby in another AZ | 60–120s automatic | **No** | ~2× |
| **Multi-AZ DB Cluster (new)** | 2 readable standbys, semi-sync | ~35s | **Yes** | ~3× |
| Read replicas | Async, readable, separate region ok | Manual promotion | Yes | Per replica |

For production: **Multi-AZ**. Downtime during patching drops from minutes to ~30s.

**2. Storage autoscaling.**
RDS can grow GP3/GP2 volumes up to a ceiling without downtime. Set a ceiling (e.g., 500GB) so a runaway write doesn't silently cost you.

**3. Automated backups + PITR.**
RDS snapshots daily + captures 5-min WAL. You can **restore to any point** within the backup window (7–35 days). Manual snapshots are retained until you delete them.

**4. Parameter groups + Option groups.**
- Parameter group = `postgresql.conf`. E.g., `shared_buffers`, `max_connections`. Some changes need reboot.
- Option group = add-on features (less relevant for Postgres; more for SQL Server/Oracle).

**5. RDS Proxy.**
Pooling layer that sits between app and DB. Useful when you have many short-lived connections (serverless / containers) — stops you from exhausting Postgres's `max_connections`. Also handles **Secrets Manager password rotation transparently**.

**6. IAM auth for Postgres.**
You can authenticate with IAM tokens instead of a password — 15-min temporary tokens, no password rotation at all. Nice for apps using IRSA.

### How you'd implement it for this project

**Your existing DB subnets already exist** in `terraform/main.tf` (`aws_subnet.db_private` across 2 AZs). Add:

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db"
  subnet_ids = [for s in aws_subnet.db_private : s.id]
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db_sg.id
  source_security_group_id = aws_security_group.app_sg.id  # or EKS pod SG
}

resource "random_password" "db" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/postgres/password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

resource "aws_db_instance" "postgres" {
  identifier              = "${var.project_name}-postgres"
  engine                  = "postgres"
  engine_version          = "15.5"
  instance_class          = "db.t3.medium"
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_type            = "gp3"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds.arn

  db_name                 = "studentdb"
  username                = "postgres"
  password                = random_password.db.result

  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.db_sg.id]
  multi_az                = true
  publicly_accessible     = false

  backup_retention_period = 14
  backup_window           = "03:00-04:00"
  maintenance_window      = "Sun:04:00-Sun:05:00"
  deletion_protection     = true
  skip_final_snapshot     = false

  performance_insights_enabled    = true
  monitoring_interval             = 60
  enabled_cloudwatch_logs_exports = ["postgresql"]

  apply_immediately = false   # ← wait for maintenance window
}
```

**Your Flask app already reads DB creds from a K8s Secret** (synced by ESO). Point ESO at the Secrets Manager entry instead of Vault:

```yaml
# helm/external-secrets/templates/externalsecret-db.yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: studentdb-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: aws-secretsmanager
  target:
    name: postgres-secret
  data:
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: two-az-network/postgres/password
```

App reads `POSTGRES_HOST=<rds-endpoint>` from values.yaml and `POSTGRES_PASSWORD` from the K8s Secret. Zero app code changes.

### Gotchas

- **DB subnet group needs ≥2 AZs** even for single-AZ RDS. Your existing subnets cover this.
- **Public accessibility defaults to true** — always explicitly set `publicly_accessible = false`.
- **Deletion protection is not the default.** Set `deletion_protection = true` + `skip_final_snapshot = false`. Without these, a `terraform destroy` nukes your DB instantly.
- **Changing certain attributes (identifier, engine) forces replacement** — which means a new DB with no data. Use `lifecycle { ignore_changes = [...] }` or the `moved {}` block to rename safely.
- **`apply_immediately = true` for parameter group changes restarts the DB right now.** Leave it false in prod.
- **Connection limits.** `db.t3.medium` ≈ 200 `max_connections`. A Flask app with 10 pods × 20 gunicorn workers = 200 connections = your cap. Add **RDS Proxy** or reduce workers per pod.
- **`random_password` in state.** Marked sensitive, but still in the state file. That's why we use Secrets Manager instead of hard-coding.

### Interview Q&A

1. **Multi-AZ vs Read Replica — difference?**
   > Multi-AZ: **synchronous** standby for HA, **not readable**. Read replica: **async**, readable, used for read scaling or cross-region DR. Different problems.

2. **Your RDS CPU is 95%. Walk me through diagnosis.**
   > Performance Insights → top wait events + top SQL. Often: missing index (seq scan), lock contention, N+1 from ORM, or genuine load. Options: add index, scale instance class, add a read replica and route SELECTs there.

3. **Explain Point-in-Time Recovery.**
   > RDS captures WAL continuously during the backup window. You can restore to any second within that window. It creates a **new** DB instance from the restore — the old one isn't modified. Typical DR drill.

4. **How do you rotate the DB password with zero downtime?**
   > Secrets Manager's **managed rotation** for RDS: Lambda creates a new password in the DB (`ALTER USER`), writes it as a new secret version, apps refetch on auth failure. Even better: **RDS Proxy** intercepts auth and handles rotation transparently.

5. **Why not just run Postgres on EKS with a StatefulSet?**
   > You can, but: (a) you own backups, patching, failover playbooks; (b) you have to reason about PVC ownership, zonal affinity, PDBs; (c) no managed HA. RDS pays for itself the first time Multi-AZ catches a hardware fault at 3am.

---

## Service 5: IAM + IRSA

### What it is

**IAM** (Identity and Access Management) is AWS's permission system. Every API call is checked: "Is this principal allowed to do this action on this resource?"

**IRSA** (IAM Roles for Service Accounts) = how a Kubernetes pod gets AWS credentials without static keys.

### Your project today uses K8s RBAC; on AWS you add IAM on top

Inside the cluster: RBAC decides which K8s operations a pod/user can do (get pods, list secrets). **IRSA** extends that so a pod can also do AWS operations (read from Secrets Manager, write to S3, pull from ECR). IRSA replaces "mount an AWS access key as a Secret."

### Key concepts you must know

**1. Principals, policies, resources.**

| Principal | Attaches to | Use |
|-----------|-------------|-----|
| **Root user** | Account creator | Never use after setup. Lock away with MFA. |
| **IAM User** | Humans (legacy) / CI (legacy) | Prefer SSO + roles |
| **IAM Role** | Assumable — EC2, Lambda, pods | **Preferred everywhere** |
| **Federated** | Users from Okta / Google / GitHub OIDC | Humans + CI in 2025 |

**2. Policy evaluation (the order interviewers love to ask):**

```
Explicit Deny anywhere → DENY
else SCP at org level must allow → else DENY
else identity-based or resource-based must allow
else permissions boundary must allow (if set)
else session policy must allow (if set)
else → DENY (implicit)
```

The #1 interview pattern: **"Why is my role allowing list but denying get?"** — the denial is probably in a KMS key policy (for SSE-KMS) or a resource-based policy, not the identity policy they're staring at.

**3. IRSA — the full flow:**

```
1. EKS exposes an OIDC provider:
   https://oidc.eks.us-east-1.amazonaws.com/id/<CLUSTER_ID>

2. You create an IAM role with a trust policy:
   { Principal: Federated = <that OIDC provider ARN>,
     Action: sts:AssumeRoleWithWebIdentity,
     Condition: StringEquals on
       "oidc.eks.us-east-1.amazonaws.com/id/<ID>:sub":
         "system:serviceaccount:<namespace>:<serviceaccount-name>" }

3. Annotate the ServiceAccount:
   eks.amazonaws.com/role-arn: arn:aws:iam::<acct>:role/<role>

4. Pod mounts a projected token → SDK calls sts:AssumeRoleWithWebIdentity
   → temporary credentials injected as env vars:
     AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
```

Result: the pod — and **only** pods using that specific SA in that namespace — can call AWS APIs with that role's permissions.

**4. Least privilege — an IAM policy per workload, not one big admin role.**

For your Flask app that reads DB password from Secrets Manager, the policy is:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
    "Resource": "arn:aws:secretsmanager:us-east-1:<acct>:secret:two-az-network/postgres/*"
  }]
}
```

Not `"*"` on actions. Not `"*"` on resources. Not `secretsmanager:*`.

**5. External ID for 3rd parties.**
When you let a vendor assume a role, include `sts:ExternalId` condition with a unique-per-customer string. Prevents "confused deputy" attacks.

### How you'd implement it for this project

**Roles you'd create:**

| Role | Purpose | Trust |
|------|---------|-------|
| `github-actions-ecr-push` | CI pushes images | OIDC from GitHub |
| `external-secrets-operator` | ESO reads secrets | IRSA (eso SA in external-secrets ns) |
| `flask-app` | (optional) app reads/writes S3 | IRSA (flask-app SA in student-api ns) |
| `aws-load-balancer-controller` | Manages ALBs | IRSA |
| `karpenter` | Provisions nodes | IRSA |
| `ebs-csi-controller` | Attaches EBS volumes | IRSA |

**Example: IRSA for the External Secrets Operator:**

```hcl
data "aws_iam_policy_document" "eso_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:sub"
      values   = ["system:serviceaccount:external-secrets:external-secrets"]
    }
  }
}

resource "aws_iam_role" "eso" {
  name               = "eso-secretsmanager-reader"
  assume_role_policy = data.aws_iam_policy_document.eso_trust.json
}

resource "aws_iam_role_policy" "eso_secrets" {
  role = aws_iam_role.eso.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      Resource = "arn:aws:secretsmanager:*:*:secret:${var.project_name}/*"
    }]
  })
}
```

Then in `helm/external-secrets/values.yaml`:

```yaml
serviceAccount:
  create: true
  name: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::<acct>:role/eso-secretsmanager-reader
```

Done. ESO pods now authenticate to AWS as this role, scoped to your project's secrets.

### Gotchas

- **"AccessDenied" even though my policy allows it** — check in this order: (a) SCP at org level, (b) explicit Deny, (c) KMS key policy (for encrypted resources), (d) resource-based policy (S3, SQS), (e) `iam:PassRole` for launch configs.
- **IRSA trust condition mismatch** — the `Condition.StringEquals` must exactly match `system:serviceaccount:<ns>:<sa>`. Typos are silent failures.
- **IAM is eventually consistent.** New roles/policies can take seconds-to-minutes to propagate. Don't retry too fast.
- **`iam:PassRole` is needed by the caller, not the callee.** To launch an EC2 with an instance profile, the launcher needs `iam:PassRole` on that role's ARN.
- **Don't grant `*` on resources "temporarily."** It never gets tightened.
- **Root user bypasses SCPs and IAM.** Enable hardware MFA on root, store credentials in a safe, never use them.

### Interview Q&A

1. **IAM user vs IAM role — why prefer roles?**
   > Users have long-lived credentials (password, access keys) that can leak. Roles have **no credentials** — they're assumed, yielding temporary tokens (15 min – 12 hrs). Leaked? Expires automatically. Use roles for everything except break-glass human accounts.

2. **Walk me through IRSA.**
   > (Deliver the 4-step flow above verbatim.)

3. **What does `iam:PassRole` guard against?**
   > Privilege escalation. Without it, anyone who can create an EC2 could pass an admin role to it and run arbitrary code with those permissions. `iam:PassRole` lets you restrict which roles a principal can attach to launched resources.

4. **Describe a policy evaluation outcome when both identity and resource policies are involved (e.g., cross-account S3).**
   > Cross-account: **both** sides must allow. Identity policy in account A (the caller) grants S3 GetObject. Bucket policy in account B grants that principal GetObject. If either is missing, Deny.

5. **How do you rotate AWS credentials used by CI?**
   > You don't — you remove them. OIDC federation (GitHub Actions → AWS IAM role) means CI assumes a role per job, gets 15-60 min creds, done. No keys to rotate.

---

## Service 6: Secrets Manager

### What it is

A managed secrets store. Encrypted at rest (KMS), versioned, access-controlled via IAM, with optional automatic rotation via Lambda functions.

### Your project today uses Vault + ESO; on AWS you'd use Secrets Manager + ESO (keeping ESO)

You already have the pattern: **External Secrets Operator** syncs secrets from an external store into Kubernetes `Secret` objects. Right now that store is Vault. On AWS, you point ESO at Secrets Manager (or SSM Parameter Store for cheap configs).

**You don't rewrite your apps.** Apps still read `POSTGRES_PASSWORD` from a K8s Secret mounted as env var. The magic happens in ESO config.

### Secrets Manager vs SSM Parameter Store

| | **Secrets Manager** | **SSM Parameter Store** |
|---|---|---|
| Cost | $0.40/secret/month + API calls | Free (Standard), $0.05/advanced |
| **Rotation** | **Built-in Lambda-based (RDS/Aurora native)** | DIY |
| Size limit | 64 KB | 4 KB (Std), 8 KB (Adv) |
| Cross-account | Resource policy | Resource policy (Advanced only) |
| Versioning | Yes | Yes |
| When to pick | DB creds, API keys needing rotation | Config, feature flags, plaintext non-secrets |

**Rule of thumb:** Secrets Manager for anything rotatable; Parameter Store for everything else. Your project's DB password → Secrets Manager. Your feature flags or Prometheus scrape interval → Parameter Store.

### Key concepts you must know

**1. Automatic rotation for RDS.**
Secrets Manager has a built-in rotation Lambda for RDS Postgres/MySQL. Flip one toggle, it rotates on schedule, zero downtime (reader gets both old+new password during transition).

**2. Resource-based policies.**
Each secret can have its own policy. Useful for cross-account: "let account B's IAM role read this specific secret."

**3. Versioning + staging labels.**
Every write creates a new version. Labels (`AWSCURRENT`, `AWSPREVIOUS`, `AWSPENDING`) point at specific versions. During rotation, Lambda promotes `AWSPENDING` → `AWSCURRENT` atomically.

**4. Cache on the client.**
Don't fetch every call. Use the AWS Secrets Manager SDK's cache or ESO's `refreshInterval` (default 1h is fine for DB passwords).

### How you'd implement it for this project

**Terraform — create a secret + rotation for RDS:**

```hcl
resource "aws_secretsmanager_secret" "db" {
  name                    = "${var.project_name}/postgres/credentials"
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = "postgres"
    password = random_password.db.result
    host     = aws_db_instance.postgres.address
    port     = 5432
    dbname   = "studentdb"
  })
}

# Optional: built-in rotation Lambda
resource "aws_secretsmanager_secret_rotation" "db" {
  secret_id           = aws_secretsmanager_secret.db.id
  rotation_lambda_arn = aws_lambda_function.rds_rotator.arn
  rotation_rules {
    automatically_after_days = 30
  }
}
```

**Wire ESO to Secrets Manager** — swap out your current Vault `ClusterSecretStore`:

```yaml
# helm/external-secrets/templates/clustersecretstore-aws.yaml
apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

**And the ExternalSecret** (same shape you already use, different `remoteRef.key`):

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: studentdb-secrets
  namespace: student-api
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: postgres-secret
    creationPolicy: Owner
  data:
    - secretKey: POSTGRES_PASSWORD
      remoteRef:
        key: two-az-network/postgres/credentials
        property: password
    - secretKey: POSTGRES_USER
      remoteRef:
        key: two-az-network/postgres/credentials
        property: username
```

Your Flask Deployment keeps reading from `postgres-secret` — **zero app changes**. Only the source of the secret moved.

### Gotchas

- **`recovery_window_in_days` defaults to 30.** If you `terraform destroy` a secret, it's soft-deleted for 30 days — you can't create a new one with the same name until then. For dev/test, set to `0` (immediate deletion); for prod, keep 30 (disaster protection).
- **KMS dependency.** Reading a KMS-encrypted secret needs both `secretsmanager:GetSecretValue` AND `kms:Decrypt` on the CMK. Miss the KMS grant → "AccessDenied" with an unclear error.
- **Rotation Lambda needs VPC access to reach RDS.** If RDS is in a private subnet (it should be), the rotator Lambda needs subnet + SG config.
- **Apps cache stale passwords.** After rotation, apps hitting DB with old password fail until they refetch. Best: connection-error retry → refetch → reconnect. Or use **RDS Proxy** (handles this transparently).
- **`secretsmanager:ListSecrets` needs `*` resource.** You can't list a specific secret — listing is account-wide. Use it sparingly.

### Interview Q&A

1. **Secrets Manager vs Parameter Store — when each?**
   > Secrets Manager: rotating credentials (DBs, API keys), costs $0.40/secret/mo, RDS-native rotation. Parameter Store: config, feature flags, non-rotating — free (Std). Rule: rotation → SM, else PS.

2. **Explain automatic rotation for an RDS password.**
   > Secrets Manager invokes a Lambda (from its library) with 4 steps: `createSecret` (new password in AWSPENDING), `setSecret` (ALTER USER on DB), `testSecret` (connect with new), `finishSecret` (promote AWSPENDING → AWSCURRENT). The app re-authenticates on failure and picks up the new password.

3. **You're seeing "AccessDeniedException" on GetSecretValue. What do you check?**
   > (a) Principal has `secretsmanager:GetSecretValue` on the secret ARN. (b) Secret's resource policy doesn't explicitly deny. (c) Principal has `kms:Decrypt` on the secret's KMS key. (d) KMS key policy allows the principal.

4. **How does ESO authenticate to Secrets Manager on EKS?**
   > Via IRSA — the ESO ServiceAccount is annotated with an IAM role ARN whose trust policy allows the EKS OIDC provider + that specific SA. ESO pod gets temp STS creds via projected token → uses them to call Secrets Manager.

5. **Why use ESO instead of Secrets Store CSI Driver?**
   > Both work. ESO materializes secrets as native K8s Secrets — simpler mental model, compatible with everything. CSI Driver mounts them directly as files, no K8s Secret created — slightly more secure (secret never in etcd) but more coupling. ESO's nicer for GitOps.

---

## Service 7: ALB + Route 53 + ACM

These three are inseparable for "give me a public HTTPS URL."

### What they are

- **Application Load Balancer (ALB)** — L7 HTTP(S) load balancer. Routes by path/host/header/method/query.
- **Route 53** — DNS. Holds your `example.com` hosted zone, answers queries, supports health-checked failover.
- **AWS Certificate Manager (ACM)** — free public TLS certs with auto-renewal. Attaches to ALB / CloudFront / API Gateway.

### Your project today uses minikube nginx (local); on AWS you'd use ALB + Route 53 + ACM

In minikube: `kubectl get ingress` returns an internal IP, you hit it via `/etc/hosts`. On AWS: the **AWS Load Balancer Controller** watches your Ingress resources and provisions an ALB in your public subnets. Route 53 points `api.example.com` at the ALB. ACM provides `*.example.com` cert. Zero manual cert management.

### Key concepts you must know

**1. Ingress → ALB (via controller).**
Install `aws-load-balancer-controller` (Helm chart). It watches Ingress objects with `ingressClassName: alb` and creates ALBs in AWS.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: flask-api
  namespace: student-api
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip            # pod IPs directly (vs instance NodePort)
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:<acct>:certificate/<id>
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/group.name: shared         # share one ALB across ingresses
spec:
  ingressClassName: alb
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: flask-api-service
                port:
                  number: 5000
```

Controller sees this → creates ALB → listener on 443 with your ACM cert → target group pointing at Flask pod IPs.

**2. Alias records vs CNAME.**
Route 53 **Alias** is AWS-specific — lets you point a **zone apex** (`example.com`) at an ALB/CloudFront/S3 website. Regular CNAMEs cannot be set at an apex. Always prefer Alias when the target is AWS.

**3. ACM cert validation.**
Two methods:
- **DNS validation** — add a `_validation` CNAME record to Route 53. Auto-renews forever.
- **Email validation** — old, fragile.
DNS is what you want. With Terraform + Route 53 it's ~10 lines.

**4. Health checks.**
ALB health-checks targets on a path you specify (`/health`). Unhealthy targets are drained. Deregistration delay (default 300s) gives in-flight requests time to finish before terminating a target.

**5. SSL/TLS offload.**
ALB terminates TLS. Backend traffic can be HTTP (cheap) or HTTPS end-to-end (compliance). Inside a private subnet with an SG-restricted target group, HTTP is usually fine.

### How you'd implement it for this project

**Terraform: hosted zone + cert + records.**

```hcl
resource "aws_route53_zone" "main" {
  name = "example.com"
}

resource "aws_acm_certificate" "main" {
  domain_name               = "example.com"
  subject_alternative_names = ["*.example.com"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options :
    dvo.domain_name => { name = dvo.resource_record_name, record = dvo.resource_record_value, type = dvo.resource_record_type }
  }
  zone_id = aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}
```

**Install ALB Controller** (Helm, with IRSA):

```bash
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$ROLE_ARN
```

**Point DNS at the Ingress's ALB** — use **ExternalDNS** controller so DNS updates automatically from Ingress annotations:

```yaml
# ingress annotation ExternalDNS watches:
external-dns.alpha.kubernetes.io/hostname: api.example.com
```

ExternalDNS creates/updates the Route 53 Alias A record automatically when the ALB appears. No manual `terraform apply` for DNS.

### Gotchas

- **`target-type: instance` vs `ip`.** `instance` sends traffic via NodePort → kube-proxy → pod (extra hop, less precise). `ip` sends directly to pod IPs (requires VPC CNI, which you have). Always use `ip` on EKS.
- **`group.name` shares one ALB across Ingresses.** Without it, every Ingress creates its own ALB ($20/mo each). With it, many Ingresses share one ALB grouped by annotation.
- **ACM certs are regional.** An ALB in us-east-1 needs an ACM cert in us-east-1. CloudFront certs must be in us-east-1 specifically (global edge).
- **Cert validation never completes.** Usually: the validation CNAME isn't propagating because your hosted zone isn't authoritative. Check NS records at your registrar.
- **ALB SGs are inferred** by the controller — but you can override. If you need to lock down ALB → only VPN traffic, set SG explicitly.
- **Slow pod readiness breaks health.** Deregistration delay is 300s; if pods take 2 min to become ready, rollouts can look broken. Tune `alb.ingress.kubernetes.io/target-group-attributes: deregistration_delay.timeout_seconds=30`.

### Interview Q&A

1. **ALB vs NLB — when pick which?**
   > ALB: L7 (HTTP), routes by path/host/header, terminates TLS, WAF integration, OIDC auth built-in. NLB: L4 (TCP/UDP), ultra-low latency, preserves client IP, gets a static IP/EIP per AZ, millions of conn/sec. Pick ALB for web apps, NLB for non-HTTP or when you need static IPs (PrivateLink services).

2. **How does the AWS Load Balancer Controller work?**
   > It runs as a deployment in the cluster with IRSA. Watches `Ingress` objects with `ingressClassName: alb`. For each one, calls AWS APIs (`elbv2:CreateLoadBalancer`, `elbv2:CreateTargetGroup`, `elbv2:CreateListener`) to provision the ALB, then syncs pod IPs into the target group. Deletes things when Ingresses go away.

3. **Why Alias record vs CNAME?**
   > CNAME can't exist at the apex of a zone (`example.com` itself). Alias is AWS's extension on A/AAAA records that points at an AWS resource. Free queries (Route 53 doesn't charge for alias resolution). Use Alias wherever possible.

4. **Your cert isn't validating. Where do you look?**
   > ACM shows "Pending validation" → check that the `_validation` CNAME exists in the hosted zone AND that the hosted zone is authoritative for the domain (NS records at the registrar point to Route 53). Propagation after that is usually <5 min.

5. **How do you do a canary deployment with ALB?**
   > (a) Target group with weighted routing: two target groups, ALB listener rule with weights (e.g., 95/5). Shift over time. (b) Argo Rollouts with ALB target-group integration — handles the weighting + automated rollback on SLI breach. Option (b) is what you want in production.

---

## Service 8: S3

### What it is

**Simple Storage Service** — AWS's object store. Unlimited objects up to 5 TB each. 11 nines durability. Access by HTTPS API or by `s3://bucket/key`.

### Your project would use S3 for (in order of priority)

1. **Terraform state backend** — `backend "s3"` with DynamoDB table for locking. **Must do.**
2. **RDS automated backups to S3** — AWS manages this, you just see it.
3. **Application artifacts** — CI build outputs, locust test results, pdf exports.
4. **Log archives** — VPC Flow Logs, ALB access logs, CloudTrail.
5. **Static assets** — if your Flask app ever serves static files + React frontend.

### Key concepts you must know

**1. Storage classes.**

| Class | Use | First-byte | Min charge |
|-------|-----|-----------|------------|
| **Standard** | Hot data | ms | — |
| **Intelligent-Tiering** | Unknown access pattern | ms (frequent tier) | 30d |
| **Standard-IA** | Infrequent | ms | 30d |
| **One Zone-IA** | Reproducible, single-AZ OK | ms | 30d |
| **Glacier Instant Retrieval** | Archive, ms reads | ms | 90d |
| **Glacier Flexible / Deep Archive** | Long-term compliance | minutes–hours | 90d / 180d |

Use **lifecycle rules** to transition objects between classes automatically.

**2. Block Public Access.**
Account-level + bucket-level toggle. **Turn on everywhere by default.** Protects against accidentally exposing a bucket via a wrong policy.

**3. Versioning.**
Keeps every version of an object. A "delete" becomes a delete-marker — original is recoverable. Essential for Terraform state buckets (can recover from bad `terraform apply`).

**4. Encryption.**
- **SSE-S3** — S3-managed key, free.
- **SSE-KMS** — your CMK, audit trail, key policy control.
- **DSSE-KMS** — double-layer encryption for FIPS contexts.
- Enable **default encryption** on the bucket so every upload gets encrypted.

**5. Access control — in 2025 you want.**
- `BlockPublicAcls = true`
- `IgnorePublicAcls = true`
- `BlockPublicPolicy = true`
- `RestrictPublicBuckets = true`
- Object Ownership: **"Bucket owner enforced"** (disables ACLs entirely)
- Bucket policy for cross-account, nothing else.

### How you'd implement it for this project

**Terraform state backend — do this FIRST, before anything else:**

```hcl
# terraform/backend.tf (bootstrap this bucket manually or in a separate stack)
resource "aws_s3_bucket" "tfstate" {
  bucket = "flask-rest-api-tfstate-${data.aws_caller_identity.current.account_id}"
}
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" kms_master_key_id = aws_kms_key.s3.arn } }
}
resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
resource "aws_dynamodb_table" "tfstate_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute { name = "LockID" type = "S" }
}
```

Then in every other Terraform stack:

```hcl
terraform {
  backend "s3" {
    bucket         = "flask-rest-api-tfstate-<account-id>"
    key            = "network/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

**Application log archive with lifecycle:**

```hcl
resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-logs-${data.aws_caller_identity.current.account_id}"
}
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    id = "archive"
    status = "Enabled"
    transition { days = 30  storage_class = "STANDARD_IA" }
    transition { days = 90  storage_class = "GLACIER" }
    expiration { days = 365 }
  }
}
```

### Gotchas

- **`force_destroy = true` on a bucket deletes everything in it.** Scary, useful for dev. Never in prod.
- **Versioned bucket + lifecycle expiration** — make sure you're expiring both current AND noncurrent versions, otherwise deleted versions accumulate forever.
- **CloudTrail data events are OFF by default.** S3 object-level GetObject / PutObject aren't logged unless you enable them (charged separately). Enable for sensitive buckets.
- **Cross-region replication costs.** It's per-GB replicated. Only replicate what matters (state bucket — yes; build artifacts — probably no).
- **Bucket names are global.** Someone else may have taken your preferred name. Use `${project}-${env}-${account-id}` to guarantee uniqueness.
- **Pre-signed URLs don't respect Block Public Access.** A valid pre-signed URL works regardless; BPA protects against wide-open ACLs/policies, not URL-based sharing.

### Interview Q&A

1. **How would you store Terraform state on AWS?**
   > S3 bucket with versioning + SSE-KMS + Block Public Access + bucket policy scoped to the ops IAM role. DynamoDB table for state locking (`hash_key = "LockID"`). `terraform { backend "s3" {...} }` in every stack.

2. **S3 accidentally made public. What do you do?**
   > (a) Enable Block Public Access at account + bucket. (b) Audit bucket policy + ACLs, strip public grants. (c) Enable "Bucket owner enforced" to disable ACLs going forward. (d) Parse CloudTrail data events + S3 access logs for external reads during the exposure window. (e) Rotate anything sensitive. (f) Add AWS Config rule + Access Analyzer for continuous detection.

3. **Which storage class for CI build logs kept 1 year?**
   > Lifecycle: Standard → Standard-IA (after 30d) → Glacier Flexible (after 90d) → Expire at 365d. Or Intelligent-Tiering if access is unpredictable.

4. **SSE-KMS vs SSE-S3 — why pay for KMS?**
   > SSE-S3 uses an S3-managed key — no audit trail, no fine-grained access control. SSE-KMS uses your CMK — every decrypt is in CloudTrail, key access is gated by the key policy (e.g., deny access outside office hours). Pick SSE-KMS for anything sensitive.

5. **How does S3 achieve 11 nines of durability?**
   > Each object is replicated across ≥3 AZs in the region, with checksums. Continuous integrity verification; auto-repair on detected corruption. Individual drive/server failures are transparent to you.

---

## Service 9: CloudWatch + AMP/AMG

### What it is

- **CloudWatch Metrics** — time-series store for AWS service metrics + custom metrics.
- **CloudWatch Logs** — log aggregation with retention, subscription filters, metric filters, Logs Insights queries.
- **CloudWatch Alarms** — threshold-based alerts → SNS / EventBridge.
- **AMP (Amazon Managed Service for Prometheus)** — managed Prometheus-compatible TSDB. You keep your PromQL and scrape configs.
- **AMG (Amazon Managed Grafana)** — managed Grafana. Same dashboards.

### Your project today uses OSS Prometheus + Grafana + Loki; on AWS you have two choices

**Option A — Keep OSS on EKS** (minimal changes)
Run your existing `helm/prometheus`, `helm/grafana`, `helm/loki` unchanged. Ship a copy of relevant metrics to CloudWatch Metrics via CloudWatch Agent or Fluent Bit for AWS-service-alarm integration.

**Option B — Move metrics to AMP, dashboards to AMG**
- Your Prometheus `remote_write` to AMP (ingestion endpoint).
- AMG dashboards point at AMP as a data source.
- Less ops — no PVC tuning, no Prometheus OOM risk, no Grafana upgrades.

**Logs**: either keep Loki on EKS, or swap to **CloudWatch Logs + Logs Insights**. CloudWatch Logs is simpler; Loki is cheaper at very high volume.

**Recommendation for this project:** start with Option A (keep OSS, ship selective metrics to CloudWatch). Move to AMP/AMG if the Prometheus instance starts needing real care.

### Key concepts you must know

**1. Metric Filters.**
Extract a metric from a CloudWatch Logs stream via pattern matching. Example: count `ERROR` lines → `FlaskAppErrors` metric → alarm on rate.

**2. CloudWatch Logs Insights query language.**

```
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
| sort @timestamp desc
```

SQL-ish, fast enough for ad-hoc digging.

**3. Embedded Metric Format (EMF).**
Log structured JSON in a specific format; CloudWatch auto-extracts high-cardinality metrics without PutMetric API calls. Cheaper at scale.

**4. Cross-account observability.**
Observability Access Manager lets source accounts ship metrics/logs to a central monitoring account. Useful if you run multi-account.

**5. Retention.**
CloudWatch Logs default retention is **Never Expire** — storage costs balloon silently. Set retention on every log group (14d / 30d / 90d based on need).

### How you'd implement it for this project

**Option A: Keep OSS, ship critical metrics to CloudWatch.**

Install CloudWatch Container Insights add-on → gives you node/pod CPU/mem/disk in CloudWatch Metrics automatically. Your existing Prometheus/Grafana stack continues to serve detailed metrics.

```bash
aws eks create-addon --cluster-name $CLUSTER --addon-name amazon-cloudwatch-observability
```

**Fluent Bit for logs to CloudWatch** (replace/augment Promtail if you want centralized search across cluster + AWS services):

```yaml
# fluent-bit.conf (as DaemonSet)
[OUTPUT]
    Name              cloudwatch_logs
    Match             *
    region            us-east-1
    log_group_name    /aws/eks/${CLUSTER}/application
    log_stream_prefix ${HOSTNAME}-
    auto_create_group true
```

**Alarms** for things that should wake someone up:

```hcl
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "rds-cpu-over-85"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  period              = 60
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  statistic           = "Average"
  threshold           = 85
  dimensions = { DBInstanceIdentifier = aws_db_instance.postgres.id }
  alarm_actions = [aws_sns_topic.critical.arn]
}
```

Route SNS → Slack via **AWS Chatbot** (no Lambda needed) or via a Lambda that posts to your existing Alertmanager Slack webhook.

### Gotchas

- **Log group retention defaults to Never.** Bills creep. Always set retention.
- **CloudWatch Logs PutLogEvents quota** — 5 req/s per log stream. Use multiple streams or switch to Firehose → S3 for high volume.
- **Alarm `evaluation_periods × period`** determines how long it takes to fire. For infra alarms, 5 × 60s = 5 min detection is typical. Too short → noise; too long → late pages.
- **Composite alarms** let you combine multiple alarms with AND/OR before paging. Great for reducing alert fatigue ("page only if both error rate AND latency SLO are breached").
- **AMG costs per active user.** Fine for small teams, expensive for 50+ engineers.

### Interview Q&A

1. **Prometheus on EKS vs AMP — which?**
   > AMP if your Prometheus is starting to need operational care (OOMs, PVC tuning, HA). Keeps PromQL + remote_write-compatible — minimal app change. OSS Prometheus if the cluster is small and you want full control, or if you need features AMP doesn't support yet.

2. **How do you alert on an ERROR log line in CloudWatch?**
   > Create a **metric filter** on the log group with pattern `?ERROR` → emits a metric. Create a CloudWatch Alarm on that metric (`Sum > 5 in 5m`) → SNS → Slack. No polling, no custom code.

3. **What's Embedded Metric Format (EMF)?**
   > A log format where structured JSON embeds metric definitions. CloudWatch auto-extracts them as metrics at ingestion. Cheaper than PutMetricData for high-cardinality custom metrics.

4. **CloudWatch Logs vs Loki — tradeoffs?**
   > CloudWatch: zero-ops, integrates with every AWS service, pay per GB ingested + stored + queried. Loki: cheaper at high scale (indexes labels only, logs in S3), OSS, Grafana-native. For most workloads, CloudWatch wins on ops simplicity; at petabyte scale Loki wins on cost.

5. **How do you get a p99 latency SLI on a Flask endpoint?**
   > Histogram metric `flask_http_request_duration_seconds_bucket` from `prometheus-flask-exporter`. In PromQL: `histogram_quantile(0.99, sum by (le) (rate(flask_http_request_duration_seconds_bucket[5m])))`. Alarm when that exceeds your SLO target.

---

## Service 10: KMS

### What it is

**Key Management Service** — AWS's hardware-backed encryption key manager. Keys never leave FIPS 140-2 validated HSMs.

### Why every other service on this list touches KMS

- RDS storage encrypted with a CMK
- Secrets Manager secrets encrypted with a CMK
- S3 SSE-KMS
- EBS volumes on EKS nodes encrypted with a CMK
- CloudWatch Logs can be encrypted with a CMK

KMS is the encryption thread that runs through every other service. Worth 10 minutes of interview time in isolation.

### Key concepts you must know

**1. Envelope encryption — why KMS is efficient.**

```
plaintext ──encrypt with DEK──► ciphertext (stored alongside encrypted DEK)
DEK       ──encrypt with CMK──► encrypted DEK (stored with ciphertext)
CMK stays in HSM. Never exported.
```

Your app asks KMS to generate a data key → KMS returns `(plaintext DEK, encrypted DEK)` → your app encrypts bytes with the plaintext DEK, stores ciphertext + encrypted DEK, discards the plaintext DEK. Later: send encrypted DEK back to KMS → get plaintext DEK → decrypt data → discard.

The CMK is never used on the data directly. KMS can handle millions of small DEK generate/decrypt requests cheaply.

**2. Key types.**

| Type | Control | Use |
|------|---------|-----|
| AWS-owned | AWS manages | Default encryption for some services; you don't see it |
| AWS-managed (`aws/rds`, `aws/s3`) | AWS rotates annually; you see it, can't delete | Quick win |
| **Customer-managed (CMK)** | You control — policy, rotation, deletion | Compliance, audit, cross-account |

For production, use CMKs. They cost $1/key/month.

**3. Key policy vs IAM.**
Unlike most resources, KMS **requires** an explicit Allow in the key policy for any principal — IAM alone isn't enough. This is the #1 cause of "AccessDenied" surprises. Pattern: grant IAM principals a statement in the key policy:

```json
{
  "Sid": "AllowApplicationUse",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<acct>:role/flask-app" },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
  "Resource": "*"
}
```

**4. Grants.**
Programmatic, time-limited, scoped permissions. Used when one AWS service needs to use your CMK on your behalf (e.g., EBS attaching a volume to an instance). You don't create grants manually often; services create them.

**5. Key rotation.**
- AWS-managed: automatic yearly.
- CMK: opt-in automatic yearly, OR manual (create new CMK, update alias).

Aliases (`alias/rds-key`) let you point at a CMK without hardcoding the ARN — useful for rotation.

### How you'd implement it for this project

**One CMK per purpose** (scoped blast radius):

```hcl
resource "aws_kms_key" "rds" {
  description         = "RDS storage encryption"
  enable_key_rotation = true
  policy              = data.aws_iam_policy_document.kms_rds.json
}
resource "aws_kms_alias" "rds" {
  name          = "alias/rds-${var.project_name}"
  target_key_id = aws_kms_key.rds.key_id
}

# Separate keys for secrets / s3 / ebs:
resource "aws_kms_key" "secrets" { description = "Secrets Manager encryption" enable_key_rotation = true }
resource "aws_kms_key" "s3"      { description = "S3 SSE-KMS"                 enable_key_rotation = true }
resource "aws_kms_key" "ebs"     { description = "EBS volume encryption"      enable_key_rotation = true }
```

**Key policy example** (RDS key — allows the IRSA role for ESO + the RDS service):

```hcl
data "aws_iam_policy_document" "kms_rds" {
  statement {
    sid       = "Root"
    actions   = ["kms:*"]
    resources = ["*"]
    principals { type = "AWS" identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"] }
  }
  statement {
    sid       = "RDS"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = ["*"]
    principals { type = "Service" identifiers = ["rds.amazonaws.com"] }
  }
  statement {
    sid       = "ESO"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    principals { type = "AWS" identifiers = [aws_iam_role.eso.arn] }
  }
}
```

### Gotchas

- **Key policy MUST grant the root user `kms:*`.** If you lock it out, only AWS Support can recover the key. Always include the root statement.
- **"AccessDenied" on GetObject from an SSE-KMS bucket.** You need `s3:GetObject` AND `kms:Decrypt` on the CMK. IAM alone isn't enough.
- **Encryption-in-place isn't a thing.** You can't "encrypt an existing unencrypted RDS." You create an encrypted snapshot and restore to a new instance.
- **Scheduled key deletion is 7-30 days.** If you delete a key with live data encrypted by it, you have that window to undo. Never shorten it for "real" keys.
- **Cross-region KMS calls cost latency.** Encrypt in the same region as the data. For cross-region S3 replication use multi-region KMS keys.

### Interview Q&A

1. **Explain envelope encryption.**
   > Data encrypted with a Data Encryption Key. DEK encrypted with a Customer Master Key in KMS. CMK never leaves HSM. Scales because CMK operations happen only once per object, not per byte.

2. **My user has `s3:*` in IAM but GetObject on an SSE-KMS bucket fails. Why?**
   > The user also needs `kms:Decrypt` permission on the CMK **and** the CMK's key policy must grant that user access. IAM on KMS is two-sided.

3. **What's a KMS grant, and when is it used?**
   > A lightweight, programmatic, time-limited permission. Used when an AWS service needs to use your CMK on your behalf — e.g., EBS creates a grant so a specific EC2 can attach an encrypted volume. You rarely create grants manually.

4. **How do you rotate a CMK?**
   > Automatic rotation: `enable_key_rotation = true` — AWS rotates the backing key material annually, transparently. Manual rotation: create a new CMK, update the alias, re-encrypt data (for data stored in S3/RDS that was encrypted with the old key — new encryption uses the alias → new key; old data stays readable until re-encrypted).

5. **Why would you use separate CMKs per service (RDS / S3 / Secrets) instead of one?**
   > Blast radius. If the RDS CMK policy is misconfigured and exposes it, only RDS is compromised, not S3 data. Also: per-service CloudTrail attribution makes auditing much easier.

---

## Service 11: AWS CI/CD

### What it is

AWS has its own end-to-end CI/CD stack — five separate services you compose into a pipeline:

| Service | Role | Analogous to |
|---------|------|--------------|
| **CodePipeline** | Orchestrator — defines stages, triggers, approvals | GitHub Actions workflow |
| **CodeBuild** | Runs builds in a managed container (Docker, shell, tests) | GitHub Actions runner (`ubuntu-latest`) |
| **CodeDeploy** | Deploys to EC2 / ECS / Lambda with blue/green + canary | Argo Rollouts, Spinnaker |
| **CodeArtifact** | Private package registry (npm, pip, maven) | GitHub Packages, Artifactory |
| **CodeStar Connections** | Secure link from AWS → GitHub / Bitbucket / GitLab | GitHub App |

**One service is NOT recommended in 2025:** **CodeCommit** (AWS's Git hosting). AWS stopped accepting new CodeCommit customers in 2024. Use GitHub / GitLab.

### Your project today uses GitHub Actions + ArgoCD; on AWS you have three patterns

**Pattern A — Keep everything you have (RECOMMENDED for your project):**
```
GitHub → GitHub Actions (OIDC to AWS) → ECR → ArgoCD in EKS → pods
```
You already do this. Zero AWS CI services needed. GitHub Actions is fine, ArgoCD is best-in-class for K8s GitOps. AWS OIDC gives you IAM-backed auth with no long-lived keys.

**Pattern B — Full AWS-native:**
```
GitHub → CodeStar Connection → CodePipeline → CodeBuild (tests + docker build)
       → ECR → CodeDeploy (EKS / ECS / EC2) → running app
```
Good fit if: org mandates "everything in AWS," you want CloudWatch-integrated pipeline metrics, or you're deploying to ECS/EC2/Lambda (where ArgoCD doesn't fit).

**Pattern C — Hybrid (GitHub for CI, AWS for CD):**
```
GitHub Actions → ECR → CodeDeploy (for ECS/Lambda) or ArgoCD (for EKS)
```
Useful when: the deploy target isn't Kubernetes. CodeDeploy's blue/green for ECS/EC2 is genuinely good.

**Bottom line for your project:** Pattern A. You'd mention AWS CI/CD in an interview to show you know the landscape, not because you need it.

### Key concepts you must know

**1. CodePipeline stages, actions, artifacts.**

A pipeline is a sequence of **stages** (Source, Build, Test, Deploy). Each stage has one or more **actions** (parallel or sequential). Actions pass **artifacts** (a zip file in S3) between them.

```
┌── Source ──┐    ┌── Build ─────┐    ┌── Test ────┐    ┌── Deploy ───┐
│ GitHub     │ →  │ CodeBuild    │ →  │ CodeBuild  │ →  │ CodeDeploy  │
│ (webhook)  │    │ docker build │    │ pytest     │    │ ECS/EKS/EC2 │
│            │    │ push to ECR  │    │ locust     │    │             │
└────────────┘    └──────────────┘    └────────────┘    └─────────────┘
   artifact:           artifact:          artifact:
   source.zip          imagedefs.json     test-report
```

Artifacts live in an S3 bucket (the "artifact store"). A failed stage blocks the pipeline.

**2. CodeBuild project — a `buildspec.yml` in your repo.**

```yaml
# buildspec.yml — CodeBuild reads this from the repo root
version: 0.2

phases:
  pre_build:
    commands:
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
      - export IMAGE_TAG=${CODEBUILD_RESOLVED_SOURCE_VERSION:0:7}
  build:
    commands:
      - docker build -t $ECR_REGISTRY/flask-app:$IMAGE_TAG .
      - docker push $ECR_REGISTRY/flask-app:$IMAGE_TAG
  post_build:
    commands:
      - printf '[{"name":"flask-app","imageUri":"%s"}]' "$ECR_REGISTRY/flask-app:$IMAGE_TAG" > imagedefinitions.json

artifacts:
  files: imagedefinitions.json
```

CodeBuild is analogous to a GitHub Actions job. It provisions a container from a managed image (`aws/codebuild/amazonlinux2-x86_64-standard:5.0`), runs your phases, uploads artifacts to S3.

**3. CodeDeploy deployment types.**

| Target | Strategies |
|--------|-----------|
| **EC2/On-Prem** | In-place, Blue/Green (via ASG swap) |
| **ECS** | Blue/Green (two task sets, ALB weight shift) |
| **Lambda** | Canary (10% then 100%), Linear (10% every N min), All-at-once |
| **EKS** | No native support — use ArgoCD / Argo Rollouts / Flux instead |

For EKS, **AWS does not recommend** CodeDeploy. Every serious EKS shop uses a K8s-native CD (ArgoCD, Flux, Argo Rollouts). You already picked the right tool.

**4. CodeBuild compute types + billing.**
Billed per minute of runtime. Smallest (`general1.small`, 3 GB RAM, 2 vCPU) is ~$0.005/min. A typical 5-minute CI job costs ~$0.025. At high commit frequency this adds up — usually still cheaper than self-hosted runners, though.

**5. Approvals in CodePipeline.**
Add a **Manual Approval** action before Deploy → pipeline pauses, sends SNS notification, waits for a human to click Approve in the console or via API. Common for prod gates.

### How you'd implement it for this project

**Pattern A (current) — no AWS CI services**, but worth hardening your GitHub Actions → AWS integration:

- OIDC federation for GitHub Actions → IAM role (covered in Service 3).
- Short-lived STS credentials, no access keys.
- Environments + protection rules on `production` (required reviewers).

**Pattern B (full AWS-native) — here's how it'd look:**

```hcl
# Terraform — CodeBuild project that builds + pushes to ECR
resource "aws_iam_role" "codebuild" {
  name               = "flask-app-codebuild"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken", "ecr:BatchCheckLayerAvailability", "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload"], Resource = "*" },
      { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" },
      { Effect = "Allow", Action = ["s3:*"], Resource = "${aws_s3_bucket.codepipeline.arn}/*" }
    ]
  })
}

resource "aws_codebuild_project" "flask_app" {
  name         = "flask-app-build"
  service_role = aws_iam_role.codebuild.arn

  artifacts { type = "CODEPIPELINE" }

  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true   # needed for `docker build`
    environment_variable { name = "AWS_REGION"    value = var.aws_region }
    environment_variable { name = "ECR_REGISTRY"  value = aws_ecr_repository.flask_app.repository_url }
  }

  source { type = "CODEPIPELINE" buildspec = "buildspec.yml" }
}
```

**CodePipeline definition:**

```hcl
resource "aws_codepipeline" "flask_app" {
  name     = "flask-app-pipeline"
  role_arn = aws_iam_role.codepipeline.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline.bucket
    type     = "S3"
  }

  stage {
    name = "Source"
    action {
      name             = "GitHub"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["source_output"]
      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = "akhil27051999/Flask-REST-API"
        BranchName       = "main"
      }
    }
  }

  stage {
    name = "Build"
    action {
      name             = "DockerBuild"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["source_output"]
      output_artifacts = ["build_output"]
      configuration    = { ProjectName = aws_codebuild_project.flask_app.name }
    }
  }

  stage {
    name = "Approve"
    action {
      name     = "ManualApproval"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"
      configuration = { NotificationArn = aws_sns_topic.pipeline_approvals.arn }
    }
  }

  stage {
    name = "Deploy"
    action {
      name            = "UpdateHelmValues"
      category        = "Build"                 # CodeBuild running `sed` + `git push` to GitOps repo
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["build_output"]
      configuration   = { ProjectName = aws_codebuild_project.update_helm.name }
    }
  }
}
```

Note even in Pattern B, the deploy to EKS still goes via **Git push → ArgoCD** — CodePipeline just replaces the "run sed and push" step. Pure CodeDeploy-to-EKS doesn't exist.

**Pattern C (hybrid) example — use when you add an ECS service** alongside your EKS workloads:

```
GitHub Actions → build + test + push to ECR
       │
       ▼
EventBridge rule (on ECR push)
       │
       ▼
CodePipeline (Source: ECR) → CodeDeploy Blue/Green (ECS)
```

ECR push is the trigger. CodeDeploy's ECS blue/green is genuinely nice — it runs two task sets simultaneously, shifts ALB weight, auto-rollback on CloudWatch alarm.

### Gotchas

- **CodeBuild needs `privileged_mode = true`** to do `docker build` inside the container. Easy to forget; errors are opaque.
- **CodePipeline artifact store is a regional S3 bucket.** One bucket per region per pipeline (can be shared). Missing bucket permissions cause `AccessDenied` on stage transitions.
- **CodeStar Connections require manual console approval** the first time — you click through a GitHub OAuth flow. Terraform creates the resource but `PENDING` until approved.
- **CodeBuild's default image is huge (~3 GB).** Pulls cached after first run but first runs are slow. Custom minimal images via ECR speed this up.
- **No native parallel fan-out across stages.** CodePipeline stages are sequential. Parallelism within a stage requires multiple actions — fiddly YAML.
- **Pipeline execution limits.** 1000 concurrent executions per pipeline by default; 20 pipelines per region. Plenty for most teams.
- **CodeDeploy EKS** — doesn't exist as a managed option. Don't propose it.
- **CodePipeline is NOT a drop-in GitHub Actions replacement.** GHA has reusable workflows, `matrix:`, complex `if:` expressions — CodePipeline is much simpler. Choose CodePipeline when the simplicity is a feature, not when you need rich logic.

### Interview Q&A

1. **You're starting a new project on AWS. Would you pick GitHub Actions or CodePipeline?**
   > GitHub Actions almost always. Better syntax, richer ecosystem, runs on any cloud, OIDC into AWS means no credential management. CodePipeline if: regulated org mandates AWS-only, or the workflow is very AWS-service-heavy (Lambda, ECS, Step Functions) and living inside AWS reduces egress / auth friction.

2. **Explain CodeDeploy's ECS blue/green.**
   > Two task sets (blue = current, green = new) run in parallel. ALB has two target groups. CodeDeploy shifts ALB weight from blue → green in configured increments (canary 10%/90%, linear 10%-every-minute, all-at-once). CloudWatch alarms automatically trigger rollback. Blue tasks drain after green is stable for a configured period.

3. **Your build needs `docker build`. How do you do that in CodeBuild?**
   > Set `privileged_mode = true` on the CodeBuild environment — this gives the container access to the Docker socket on the host. Then `docker build` + `docker push` work. Without it, you get "Cannot connect to the Docker daemon" errors.

4. **What replaces CodeCommit now that AWS has stopped accepting new customers?**
   > Use GitHub, GitLab, or Bitbucket. Connect to AWS via **CodeStar Connections** (for CodePipeline) or **OIDC federation** (for GitHub Actions → IAM role). AWS's direction: don't host Git, integrate with the Git hosts people already use.

5. **Why do teams running EKS usually NOT use CodeDeploy?**
   > CodeDeploy has no native K8s support. K8s-native CD tools (ArgoCD, Flux, Argo Rollouts) understand Kubernetes primitives (Deployments, Services, Ingress), support the App-of-Apps pattern, use git as the source of truth. CodeDeploy predates K8s and was built for EC2/ECS/Lambda. Use the right tool for the platform.

6. **How do you add a manual approval before production deploy?**
   > CodePipeline: add a `Manual Approval` action before the Deploy stage with an SNS topic for notifications. Pipeline pauses, reviewer approves in the console or via `aws codepipeline put-approval-result`. Equivalent in GitHub Actions: `environment: production` with required reviewers in the repo settings.

7. **What's CodeArtifact?**
   > AWS's private package registry — hosts npm, pip, maven, NuGet, gem packages. Supports upstream repos (pulls from npm.js and caches). Integrates with IAM for auth. Used when you need a private package registry and want to stay inside AWS. For most teams, GitHub Packages or Artifactory is simpler.

8. **Can a CodePipeline deploy to an EKS cluster?**
   > Indirectly. The "deploy" stage runs a CodeBuild job that either (a) `kubectl apply` / `helm upgrade` directly, or (b) commits a Helm values bump to the GitOps repo that ArgoCD watches. Option (b) is GitOps-compliant — the cluster still pulls from git, CodePipeline just writes the git commit.

---

## End-to-End Architecture

Here's the whole project on AWS, put together:

```
                    INTERNET
                       │
                       ▼
                  ┌─────────┐        ┌───────────┐
                  │Route 53 │        │    WAF    │   (optional)
                  └────┬────┘        └─────┬─────┘
                       │                   │
                       ▼                   ▼
                  ┌───────────────────────────┐
                  │    ALB (443, ACM cert)    │   in public subnets
                  └────────────┬──────────────┘
                               │ target-type: ip
┌──────────── VPC 10.0.0.0/16 ────────────────────────────────────────────────┐
│                              │                                              │
│  PRIVATE APP SUBNETS (2 AZs, 10.0.1.0/24 + 10.0.11.0/24)                    │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ EKS worker nodes (managed node group + Karpenter)               │        │
│  │                                                                 │        │
│  │  ┌─────────────────┐   ┌─────────────────┐  ┌────────────────┐  │        │
│  │  │ flask-api pod   │   │ flask-api pod   │  │ flask-api pod  │  │        │
│  │  │ (from ECR)      │   │                 │  │                │  │        │
│  │  │ IRSA: reads     │   │                 │  │                │  │        │
│  │  │ Secrets Manager │   │                 │  │                │  │        │
│  │  └────┬────────────┘   └─────────────────┘  └────────────────┘  │        │
│  │       │                                                         │        │
│  │       │ pod IP → RDS SG                                         │        │
│  └───────┼─────────────────────────────────────────────────────────┘        │
│          │                                                                  │
│          ▼                                                                  │
│  DB SUBNETS (isolated, no 0.0.0.0/0 route, 10.0.2.0/24 + 10.0.12.0/24)      │
│  ┌───────────────────────────────────────────────┐                          │
│  │ RDS Postgres (Multi-AZ, encrypted via KMS)    │                          │
│  │  writer(az-a) ←sync→ standby(az-b)            │                          │
│  └───────────────────────────────────────────────┘                          │
│                                                                             │
│  DEPENDENT SERVICES SUBNETS (ESO pod, ArgoCD, etc.)                         │
│  OBSERVABILITY SUBNETS (Prometheus/Grafana/Loki — or AMP/AMG off-cluster)   │
│                                                                             │
│  VPC ENDPOINTS: S3 (gateway), ECR api+dkr, Secrets Manager, STS, Logs       │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (outside VPC, reached via endpoints)
      ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────┐  ┌───────┐
      │   ECR   │  │ Secrets │  │   S3    │  │ KMS  │  │ CloudW│
      │(images) │  │ Manager │  │(state + │  │(CMKs)│  │ atch  │
      │         │  │(db pass)│  │ logs)   │  │      │  │(logs) │
      └─────────┘  └─────────┘  └─────────┘  └──────┘  └───────┘

   CI (GitHub Actions):                    GitOps (ArgoCD in-cluster):
   push → OIDC to IAM role →               watches helm/ + argocd/ dirs on main →
   docker build → push to ECR →            sync to cluster → Flask pods get new image
   sed image tag in values.yaml → git push
```

---

## 90-Day Implementation Roadmap

If you ever want to actually deploy this to AWS, here's the order that keeps each step shippable:

**Week 1–2: Foundation**
- [ ] Create AWS account, enable MFA on root, configure Identity Center (SSO)
- [ ] Bootstrap S3 bucket + DynamoDB for Terraform state
- [ ] Deploy your existing `terraform/` (VPC, subnets, NAT, SGs) — no changes needed
- [ ] Add VPC endpoints (S3, ECR, STS, Secrets Manager)
- [ ] Set up CloudTrail org-wide → S3

**Week 3–4: Container platform**
- [ ] Create ECR repos (flask-app, etc.) with lifecycle policies
- [ ] Wire GitHub Actions OIDC → IAM role → push to ECR (replaces DockerHub step)
- [ ] Provision EKS cluster (1 system node group) via `terraform-aws-modules/eks`
- [ ] Install add-ons: VPC CNI, CoreDNS, kube-proxy, EBS CSI
- [ ] Install AWS Load Balancer Controller (IRSA)
- [ ] Install Karpenter for autoscaling

**Week 5–6: Data + secrets**
- [ ] Provision RDS Postgres (Multi-AZ, encrypted)
- [ ] Migrate data from in-cluster Postgres to RDS (`pg_dump` | `psql`)
- [ ] Create Secrets Manager entries for DB creds
- [ ] Install External Secrets Operator with IRSA, point at Secrets Manager
- [ ] Retire in-cluster Postgres + Vault (keep them in a different ns during cutover)

**Week 7–8: Exposure**
- [ ] Register domain / set up Route 53 hosted zone
- [ ] Request ACM cert (DNS-validated)
- [ ] Install ExternalDNS → auto-creates Route 53 records
- [ ] Update Flask Ingress with ALB annotations → `api.example.com` live

**Week 9–10: Observability**
- [ ] Install CloudWatch Container Insights add-on
- [ ] Fluent Bit → CloudWatch Logs for centralized app logs
- [ ] Migrate Prometheus to AMP (remote_write)
- [ ] Migrate Grafana to AMG, re-point dashboards
- [ ] Alertmanager → SNS → Slack via AWS Chatbot

**Week 11–12: Production hardening**
- [ ] Enable GuardDuty + Security Hub
- [ ] AWS Config rules: RDS encryption, S3 public access, root MFA
- [ ] Backup plan via AWS Backup across RDS/EBS/EFS
- [ ] Run a chaos gameday — kill a node, drop an AZ, restore from RDS snapshot
- [ ] Load test with Locust — tune HPA + RDS Proxy + ALB deregistration

**Ongoing: Cost & governance**
- [ ] Cost Explorer + Budgets per tag
- [ ] Savings Plans commitment for steady-state
- [ ] Spot instances for Karpenter-provisioned nodes (stateless workloads)

---

## Cost Estimate

Rough monthly spend if this project runs in AWS with light traffic:

| Service | Config | Est. $/mo |
|---------|--------|-----------|
| EKS control plane | 1 cluster | $73 |
| EC2 (2× t3.medium nodes, on-demand) | baseline | $60 |
| EC2 via Karpenter (bursty, spot) | avg 1× t3.medium | ~$10 |
| RDS Postgres (db.t3.medium, Multi-AZ, 20GB gp3) | | ~$110 |
| ALB | 1 shared ALB, low traffic | ~$20 |
| NAT Gateway | 2 × $0.045/hr + minimal data | ~$70 |
| ECR | <10 GB | ~$1 |
| Secrets Manager | 5 secrets | ~$2 |
| CloudWatch Logs | 10 GB ingested, 14d retention | ~$5 |
| Route 53 | 1 hosted zone | $0.50 |
| ACM | Public certs | Free |
| S3 | 10 GB state + logs | ~$1 |
| Data transfer / egress | low | ~$10 |
| **Total** | | **~$360/mo** |

**Cost reduction levers (in priority order):**
1. Kill the NAT GW. Use Karpenter + spot + VPC endpoints — move to **single NAT in dev**, still multi-NAT in prod. Saves ~$40/mo.
2. Use Aurora Serverless v2 instead of RDS if traffic is bursty. Scales to zero ACUs idle.
3. Move nodes to **Spot** via Karpenter for non-prod. 70% discount. Saves ~$40/mo.
4. **1-year Compute Savings Plan** for the steady-state baseline — ~30% off.
5. S3 lifecycle on log bucket — transitions to Glacier for old logs.

Realistic target after optimizations: **~$200–230/mo** for a personal project that's actually running.

---

*That's the whole thing — 10 services, mapped to your project, deep enough to implement, tight enough to explain in an interview.*
