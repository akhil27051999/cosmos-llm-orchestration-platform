# Module 8: AWS Cloud Services (Networking, IAM/Security, Databases, Storage, and the Rest)

> **Goal:** A deep-dive reference for the AWS services a 3–5 yr DevOps/SRE is expected to design, operate, and troubleshoot in interviews and on the job. Built as the **cloud-native counterpart** to the minikube/Vault/Helm/ArgoCD stack in Modules 1–7.

> **Why this matters:** Every Kubernetes construct we deployed locally (Service, Ingress, Secret, PV, HPA, NetworkPolicy) has an AWS-native equivalent (ALB, Secrets Manager, EBS, ASG, Security Group). Interviewers routinely ask "how would you port this to AWS?" and expect you to name the right primitive, explain the tradeoffs, and debug it when it breaks.

> **Scope of this project:** The Terraform in `terraform/` targets AWS but was **not deployed** (cost avoidance). This doc is the conceptual + operational deep-dive that the Terraform reference architecture is built on.

---

## Table of Contents

1. [AWS Global Architecture](#aws-global-architecture)
2. [Part A — Networking (Deep Dive)](#part-a--networking-deep-dive)
3. [Part B — IAM & Security (Deep Dive)](#part-b--iam--security-deep-dive)
4. [Part C — Databases](#part-c--databases)
5. [Part D — Storage](#part-d--storage)
6. [Part E — Compute](#part-e--compute)
7. [Part F — Containers & Serverless](#part-f--containers--serverless)
8. [Part G — Messaging & Integration](#part-g--messaging--integration)
9. [Part H — Observability on AWS](#part-h--observability-on-aws)
10. [Part I — Cost, Governance & Organizations](#part-i--cost-governance--organizations)
11. [Cross-Cutting Troubleshooting Scenarios](#cross-cutting-troubleshooting-scenarios)
12. [STAR Stories](#star-stories)
13. [Production Hardening — Well-Architected Mapping](#production-hardening--well-architected-mapping)
14. [Mapping This Project to AWS](#mapping-this-project-to-aws)

---

## AWS Global Architecture

```
┌─────────────────────── AWS Global Infrastructure ───────────────────────┐
│                                                                         │
│  Region (us-east-1)                  Region (eu-west-1)                 │
│  ┌───────────────────────┐           ┌───────────────────────┐          │
│  │  AZ a   AZ b   AZ c   │           │  AZ a   AZ b   AZ c   │          │
│  │  ┌──┐  ┌──┐  ┌──┐     │           │  ┌──┐  ┌──┐  ┌──┐     │          │
│  │  │DC│  │DC│  │DC│     │           │  │DC│  │DC│  │DC│     │          │
│  │  └──┘  └──┘  └──┘     │           │  └──┘  └──┘  └──┘     │          │
│  └───────────────────────┘           └───────────────────────┘          │
│           │                                       │                     │
│           └───── AWS Global Backbone ─────────────┘                     │
│                                                                         │
│  Edge Locations (400+): CloudFront, Route 53, Global Accelerator,       │
│                         Lambda@Edge, AWS Shield                         │
│                                                                         │
│  Local Zones / Wavelength / Outposts: AWS services closer to users      │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key vocabulary:**

| Term | Meaning |
|------|---------|
| **Region** | A geographic area (us-east-1, eu-west-1). Isolated from other regions. Pick based on latency, compliance, and service availability. |
| **Availability Zone (AZ)** | One or more discrete datacenters inside a region. Each AZ has redundant power, networking, cooling. AZs in a region are connected by low-latency links (<2 ms). |
| **Edge Location** | PoPs (400+ worldwide) used by CloudFront, Route 53, Shield for caching and DDoS protection. |
| **Local Zone / Wavelength** | Extensions of a region to metro areas / 5G networks for ultra-low-latency. |
| **Outposts** | AWS hardware in your datacenter. Same APIs. Hybrid workloads. |

**The universal HA rule:** Deploy across **≥2 AZs**. One AZ failure should never take the application down. Multi-region is for disaster recovery and regulated latency, not routine HA.

---

## Part A — Networking (Deep Dive)

This section covers VPC, subnets, routing, internet/NAT gateways, VPC endpoints, Security Groups vs NACLs, load balancers, Route 53, CloudFront, VPC peering, Transit Gateway, PrivateLink, Direct Connect, and VPN.

### A.1 VPC (Virtual Private Cloud)

**What it is:** A logically isolated virtual network you define inside a region. CIDR block, subnets, route tables, gateways — all yours.

```
VPC: 10.0.0.0/16  (65 536 IPs)
│
├── AZ us-east-1a
│   ├── Public  subnet   10.0.1.0/24   → IGW           (ALB, NAT, Bastion)
│   ├── App    subnet    10.0.11.0/24  → NAT GW        (EC2, EKS workers)
│   ├── DB     subnet    10.0.21.0/24  → (no egress)   (RDS)
│
├── AZ us-east-1b
│   ├── Public subnet    10.0.2.0/24   → IGW
│   ├── App    subnet    10.0.12.0/24  → NAT GW
│   └── DB     subnet    10.0.22.0/24  → (no egress)
```

**Design rules:**

| Rule | Why |
|------|-----|
| CIDR `/16` for VPC, `/24` for subnets | `/24` = 256 IPs (AWS reserves 5), enough for most tiers. `/16` leaves room. |
| Never overlap CIDRs across VPCs you may peer | Peering, TGW, Direct Connect all refuse overlapping ranges. |
| Use private IPs only (RFC 1918) | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16. |
| Tier subnets by trust level (public/app/db) | Different route tables, different SGs, least-privilege blast radius. |
| ≥2 AZs per tier | Loss of one AZ still serves traffic. |

**Reserved IPs per subnet:** AWS reserves 5 — `.0` network, `.1` router, `.2` DNS, `.3` future, `.255` broadcast (even on IPv4 unicast). So a `/24` has 251 usable IPs, not 256.

### A.2 Route Tables & Internet Egress

Every subnet is **associated** with one route table. Routes say "for destination X, send to target Y."

**Public subnet route table:**
```
10.0.0.0/16   → local          (intra-VPC, implicit, immutable)
0.0.0.0/0     → igw-abc123     (everything else → Internet Gateway)
```

**Private subnet route table:**
```
10.0.0.0/16   → local
0.0.0.0/0     → nat-xyz789     (egress via NAT GW in public subnet)
```

**DB subnet route table:**
```
10.0.0.0/16   → local          (no 0.0.0.0/0 — no internet at all)
```

### A.3 Internet Gateway (IGW) vs NAT Gateway

| Aspect | **IGW** | **NAT Gateway** |
|--------|---------|-----------------|
| Role | Bidirectional internet (public subnet) | Egress-only from private subnet |
| IP needed | Resource must have public IP or EIP | NAT has an EIP; private hosts reuse it |
| Scope | 1 per VPC | 1 per AZ (for HA) |
| HA | Built-in AWS-managed | Zonal; deploy in each AZ |
| Cost | Free | **~$0.045/hr + ~$0.045/GB processed** — often the surprise AWS bill item |

**Alternative for cost:** **NAT Instance** (EC2 running iptables). Cheaper at low volumes, no HA out of the box, less bandwidth. Modern best-practice: NAT GW.

### A.4 Security Groups vs Network ACLs

| | **Security Group (SG)** | **Network ACL (NACL)** |
|---|---|---|
| Scope | ENI (attached to instance/LB/RDS) | Subnet-wide |
| Stateful? | **Yes** — return traffic auto-allowed | **No** — must allow both inbound and outbound explicitly |
| Rules | Allow only (no deny) | Allow + Deny |
| Default | Deny all inbound, allow all outbound | Default NACL: allow all both directions |
| Evaluation | All rules evaluated together | Numbered; lowest first that matches wins |
| Reference | Another SG ID (great for tiers) | Only CIDR ranges |
| Change takes effect | Immediately | Immediately |

**Tier pattern:**
```
ALB-SG:   inbound 443 from 0.0.0.0/0 (public)
App-SG:   inbound 5000 from ALB-SG
DB-SG:    inbound 5432 from App-SG
```
Referencing SG-by-SG (not CIDR) means scaling out instances changes nothing — the new ENI is in App-SG automatically.

**When to use NACL:** Broad deny rules at the subnet boundary (e.g., block a known-bad IP), defense in depth. Everyday traffic control → SGs.

### A.5 VPC Endpoints

**Why:** Traffic from a private subnet to AWS services (S3, DynamoDB, KMS, SQS, etc.) would otherwise go out the NAT GW → public internet → back to AWS. Expensive and avoidable.

| Endpoint type | Services | How it works |
|---------------|----------|--------------|
| **Gateway Endpoint** | S3, DynamoDB only | Adds a route-table entry. **Free.** |
| **Interface Endpoint** (PrivateLink) | ~100 services (KMS, SQS, SNS, ECR, EKS, etc.) | Creates ENIs with private DNS. **~$0.01/hr per AZ + $0.01/GB.** |

**Test:** `dig s3.us-east-1.amazonaws.com` from an EC2. Without endpoint → public IP. With gateway endpoint + proper route → still DNS public, but traffic stays on AWS backbone.

### A.6 Elastic Load Balancers

| Type | OSI | Use case | Health checks | Notable features |
|------|-----|----------|--------------|------------------|
| **ALB** | L7 (HTTP/HTTPS) | Web apps, microservices | HTTP path/code | Path/host/header routing, WAF integration, gRPC, HTTP/2, TLS termination, auth via OIDC/Cognito |
| **NLB** | L4 (TCP/UDP/TLS) | Ultra-low latency, millions of conn/s, static IP | TCP/HTTP | Preserves client IP, Elastic IP per AZ, PrivateLink provider |
| **GWLB** | L3 (IP) | Insertion of 3rd-party firewalls/IDS/IPS | GENEVE | Transparent traffic steering |
| **CLB** (legacy) | L4/L7 | Don't use in new designs | | Replaced by ALB/NLB |

**ALB deep dive:**
- **Listener** → one or more **Rules** → **Target Groups** (EC2/IP/Lambda targets)
- Rules can match path (`/api/*`), host (`api.example.com`), header, query, HTTP method
- **Stickiness:** cookie-based session affinity (app-generated or ALB-generated `AWSALB`)
- **Slow start:** gradually ramps traffic to newly healthy targets
- **Connection draining / Deregistration delay:** 300s default — wait for in-flight requests before removing a target

### A.7 Route 53 (DNS)

| Record type | Use |
|------|-----|
| A / AAAA | IPv4 / IPv6 |
| CNAME | Alias to another DNS name (but **not apex** — `example.com`) |
| **Alias** (AWS-specific) | Apex → ALB/CloudFront/S3 website/API Gateway. Free. Works at zone apex, unlike CNAME. |
| MX, TXT, NS, SRV | Standard |

**Routing policies:**
| Policy | Logic |
|--------|-------|
| **Simple** | One answer |
| **Weighted** | Split traffic by percentage (canary) |
| **Latency** | Send to region with lowest RTT |
| **Failover** | Primary/Secondary with health check |
| **Geolocation** | By country/continent (compliance) |
| **Geoproximity** | By geographic distance + bias (Traffic Flow feature) |
| **Multi-value** | Up to 8 healthy answers returned (basic LB) |

**Health checks:** Can monitor endpoints, other health checks, or CloudWatch alarms. Route 53 will only return healthy answers.

### A.8 CloudFront (CDN)

- **Global PoPs** cache static + dynamic content.
- Origins: S3, ALB, MediaStore, any HTTP endpoint.
- **Signed URLs / Signed Cookies** for private content.
- **Origin Access Control (OAC)** (replaces OAI) restricts S3 origin to CloudFront only.
- **Lambda@Edge / CloudFront Functions** for request/response manipulation.
- **Price classes** control which continents' PoPs you pay for.

**TTL hierarchy:** Cache-Control header on origin > CloudFront behavior TTL > default.

### A.9 Connecting VPCs & On-Prem

| Connection | Use | Notes |
|------------|-----|-------|
| **VPC Peering** | 1:1 VPC connectivity | Non-transitive; each pair needs its own peering + routes; no overlapping CIDRs |
| **Transit Gateway (TGW)** | Hub-spoke for many VPCs and on-prem | Transitive; regional; supports route tables per attachment; preferred at scale (>3-4 VPCs) |
| **PrivateLink (Interface Endpoint + NLB)** | Expose a service VPC→VPC without peering | Consumer-side ENIs; no route table changes |
| **Direct Connect (DX)** | Dedicated fiber to AWS | 1/10/100 Gbps; consistent latency; DX Gateway for multi-region |
| **Site-to-Site VPN** | IPsec over internet | Cheaper, higher latency, two tunnels per connection for HA |
| **Client VPN** | End-user OpenVPN-based access | MFA via AD/SAML |
| **CloudWAN** | Managed global WAN on top of TGW | Newer; policy-driven routing |

**Transitive routing gotcha:** VPC peering is **not** transitive. If A↔B and B↔C, A cannot reach C via B. Use TGW for that.

### A.10 Networking Troubleshooting Scenarios

1. **Pod/EC2 can't reach the internet** → check (a) subnet's route table has `0.0.0.0/0 → nat-*` or `→ igw-*`; (b) SG outbound allows 443; (c) NACL allows both directions; (d) public subnet's NAT has EIP.
2. **ALB target unhealthy** → health check endpoint returns 200? SG on target allows traffic from ALB-SG on the target port? Target in a subnet the ALB's subnets can reach (shared VPC)?
3. **Can't reach RDS from EC2** → RDS subnet group covers at least 2 AZs? RDS SG's inbound allows the EC2-SG on 5432? Correct cluster endpoint (writer vs reader)?
4. **NAT GW surprise bill** → probably a chatty process pulling from S3/ECR. Add S3 Gateway Endpoint + ECR Interface Endpoint; re-check CloudWatch `BytesOutToDestination`.
5. **CloudFront returning 502 from ALB origin** → origin SSL cert mismatch? ALB's listener 443 using valid ACM cert matching the CloudFront origin domain? Origin protocol set correctly (HTTP vs HTTPS vs match-viewer)?
6. **DNS resolves to private IP but connection times out** → you're outside the VPC or VPN. Private-hosted zone only resolves from inside the VPC (or via Route 53 Resolver endpoints).
7. **Packet drops mid-flow, not on new connections** → likely SG changed but only affects new connections because SGs are stateful. Check Flow Logs with `ACTION=REJECT`.
8. **Cross-account VPC endpoint fails** → the service endpoint's policy excludes your principal, or your SG blocks the ENI.

### A.11 Networking Interview Q&A

1. **What's the difference between a public and private subnet?**
   > Whether its route table has a `0.0.0.0/0 → IGW` route. Nothing else; there's no "public/private" flag.

2. **SG vs NACL — which is stateful, which evaluates in order?**
   > SG = stateful, all rules evaluated together. NACL = stateless, numbered rules, lowest matching number wins.

3. **Why is NAT GW per-AZ for HA?**
   > It's a zonal resource. If AZ-a goes down, a NAT GW only in AZ-a breaks all private-subnet egress in the VPC. Deploy one per AZ and route each subnet to its own-AZ NAT.

4. **Alias vs CNAME?**
   > CNAME can't be set on a zone apex (`example.com`). Alias is an AWS extension to A/AAAA that points at AWS resources (ALB, CloudFront, S3) and is free. Use Alias wherever you can.

5. **How does an ALB route to a target?**
   > Listener → rule match (path/host/header/method/query) → forward action → target group. Target group has targets + health checks + stickiness + deregistration delay.

6. **Explain the 5 reserved IPs in a subnet.**
   > `.0` = network, `.1` = VPC router, `.2` = DNS (Route 53 Resolver), `.3` = future/AWS, `.255` = broadcast (not actually usable, reserved anyway). So `/24` has 251 usable.

7. **Why would you use PrivateLink over VPC peering?**
   > To expose a single service — not the whole VPC — to a consumer VPC. No CIDR overlap concerns, one-way, fine-grained.

8. **What does Transit Gateway solve that peering doesn't?**
   > Transitive routing and centralized policy across many VPCs and on-prem. Peering is a full mesh (N² connections); TGW is hub-and-spoke.

9. **How do VPC Flow Logs help debug connectivity?**
   > They record `srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, ACTION (ACCEPT/REJECT)` per flow. If you see `REJECT` at the SG or subnet, the SG/NACL is blocking.

10. **What's the difference between Gateway Endpoint and Interface Endpoint?**
    > Gateway = route-table target for S3/DDB only, free. Interface = ENI in your subnet (PrivateLink) for ~100 services, paid by hour + GB.

11. **How does ALB preserve the client IP? And NLB?**
    > ALB does **not** — it terminates TCP. Client IP is in `X-Forwarded-For`. NLB **does** preserve client IP (TCP passthrough). Configure target-group `preserve_client_ip` if you want source IP on NLB → IP targets.

12. **What are the HTTP routing capabilities of ALB?**
    > Path, host, HTTP header, HTTP method, query string, source IP. Combined via AND/OR up to rule conditions limit.

13. **Explain ALB vs NLB for a gRPC service.**
    > ALB supports gRPC (HTTP/2) with routing + health checks. NLB handles L4 only — works, but no request-level features. Pick ALB unless you need NLB's static IP/low latency.

14. **What's a VPC Endpoint policy for?**
    > Restricts what API calls can traverse the endpoint. Example: S3 gateway endpoint policy allowing only your company's buckets.

15. **Draw the packet flow from a browser to an EKS pod behind an ALB.**
    > Browser → Route 53 → CloudFront (optional) → public IP of ALB (in public subnet) → target group IP target = pod IP (or Node + NodePort for instance mode) → kube-proxy / IP forwarding → pod veth → pod.

16. **What's a bastion host, and is it still needed?**
    > Jump host with public IP to SSH/RDP into private instances. Replaced in most orgs by **SSM Session Manager** (no open SSH, no public IP, IAM-authenticated, fully audited).

17. **Explain IPv6 in VPC.**
    > Dual-stack. VPC gets a `/56`, subnets `/64`. IGW/NAT for IPv4 still needed; for IPv6 you use **Egress-Only Internet Gateway** for outbound-only IPv6.

18. **What happens to existing connections when you change a Security Group rule?**
    > Because SGs are stateful, **existing flows keep working** until they time out. Only new flows are subject to the new rule. This is a classic trap when "revoking" access.

19. **How do you implement blue/green at the DNS layer?**
    > Two ALBs or target groups. Route 53 weighted records shift 0% → 100%. Health checks remove the bad color automatically.

20. **A VPN tunnel shows "UP" but traffic doesn't flow. Where do you look?**
    > (a) Propagation — is VGW propagating routes into the route table? (b) The **customer side** — does their route table point your CIDR at the VPN concentrator? (c) SG/NACL on the private subnet. (d) Asymmetric routing between two tunnels.

---

## Part B — IAM & Security (Deep Dive)

### B.1 IAM Core Concepts

**Principals:**

| Principal | Use |
|-----------|-----|
| **Root user** | Account owner. **Never use after setup.** Enable MFA, lock away. |
| **IAM User** | Long-lived identity for a human or legacy workload. Prefer SSO/roles. |
| **IAM Group** | Permissions bundle you attach users to. |
| **IAM Role** | Assumable identity with temporary STS credentials — for services, cross-account access, federation. **Preferred pattern.** |
| **Federated Identity** | User in an IdP (Okta, AD, Google) who assumes a role via SAML/OIDC. |

**Policies:**

| Policy type | Attached to | Purpose |
|-------------|------------|---------|
| **Identity-based** | User, group, role | "What can this principal do?" |
| **Resource-based** | S3 bucket, KMS key, SQS, Lambda, etc. | "Who can act on this resource?" |
| **Permissions boundary** | User or role | Max permissions (cap) — even if identity policy allows more |
| **Service Control Policy (SCP)** | Org / OU | Org-wide guardrail at the account level |
| **Session policy** | Passed at `sts:AssumeRole` time | Further restricts the session |
| **ACL** (legacy) | S3/VPC | Old style; prefer policies |

### B.2 Policy Document Anatomy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowListMyBuckets",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::my-bucket",
      "Condition": {
        "IpAddress": {"aws:SourceIp": ["203.0.113.0/24"]},
        "Bool":      {"aws:SecureTransport": "true"}
      }
    }
  ]
}
```

Key elements: `Effect` (Allow/Deny), `Action` (API action), `Resource` (ARN), `Principal` (only in resource-based), `Condition` (MFA, IP, VPC, tag, time).

### B.3 Policy Evaluation Logic

For any API call, AWS evaluates across all applicable policies:

```
1. Explicit Deny  anywhere → DENY (overrides everything)
2. Organization SCP does not Allow → DENY
3. Resource-based policy Allows  ────────┐
4. Identity-based policy Allows          │
5. Permissions boundary Allows           ├── All-Allow? → ALLOW
6. Session policy Allows  ───────────────┘
7. Otherwise → DENY (implicit)
```

**Cross-account:** Resource-based **or** identity-based Allow in the source account + identity-based Allow in the target account. Both sides must agree.

### B.4 STS and AssumeRole

STS (Security Token Service) issues **temporary credentials** (AccessKey + SecretKey + SessionToken + Expiry).

APIs:
- `sts:AssumeRole` — cross-account, cross-service
- `sts:AssumeRoleWithSAML` — enterprise SSO
- `sts:AssumeRoleWithWebIdentity` — OIDC (GitHub Actions, EKS pods)
- `sts:GetSessionToken` — MFA-protected session for an IAM user

**Trust policy** on the role says "who can assume me":
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::111122223333:root"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"sts:ExternalId": "unique-shared-id"}}
  }]
}
```

**External ID** prevents the "confused deputy" problem when a 3rd party assumes your role.

### B.5 Roles for Services

| Integration | Mechanism |
|-------------|-----------|
| **EC2** | Instance profile (role attached to instance metadata, apps call `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` or use IMDSv2) |
| **Lambda** | Execution role |
| **ECS/Fargate task** | Task role (app) + Task execution role (agent pulls image, writes logs) |
| **EKS pod** | **IRSA** (IAM Roles for Service Accounts) — OIDC-federated, `eks.amazonaws.com/role-arn` annotation on a ServiceAccount |
| **GitHub Actions / CI** | OIDC federation — no long-lived keys |
| **CodeBuild / CodePipeline** | Service roles |

**IMDSv2:** Session-token based. `IMDSv1` is vulnerable to SSRF; enforce IMDSv2 on all instances (`http_tokens=required`).

### B.6 KMS (Key Management Service)

**Envelope encryption** — the whole reason KMS is efficient:
```
Plaintext ──encrypt with DEK──► Ciphertext  (stored alongside encrypted DEK)
DEK       ──encrypt with CMK──► Encrypted DEK
CMK never leaves KMS hardware (HSM-backed).
```

**Key types:**

| Type | Control | Use |
|------|---------|-----|
| **AWS-owned** | AWS manages | Default encryption for many services; you don't see it |
| **AWS-managed** (`aws/s3`, `aws/rds`) | AWS rotates annually; you see it, can't delete | Quick win: enable, done |
| **Customer-managed (CMK)** | You control — policy, rotation, deletion | Required for audit, cross-account, BYOK |

**Key policy** is the resource policy on a CMK. Unlike most resources, KMS **requires** an explicit Allow in the key policy for any principal — IAM alone isn't enough.

**Grants** = lightweight, programmatic permissions (used by services like EBS to use the key on your behalf).

**Key rotation:** Automatic (AWS-managed 1-yr, CMK opt-in 1-yr), manual (create new CMK, update aliases).

### B.7 Secrets Manager vs SSM Parameter Store

| | **Secrets Manager** | **SSM Parameter Store** |
|---|---|---|
| Cost | ~$0.40/secret/mo + API calls | Free (Standard) |
| Rotation | Built-in with Lambda functions (RDS/Aurora native) | DIY |
| Size limit | 64 KB | 4 KB (Standard), 8 KB (Advanced) |
| KMS encryption | Always | SecureString only |
| Cross-account | Resource policy | Resource policy (Advanced) |
| Versioning | Yes | Yes |
| Best for | Credentials, API keys needing rotation | Config, feature flags, non-rotating secrets |

**In this project:** Vault + ESO plays the Secrets Manager role. Migration path: swap Vault provider for AWS SecretsManager provider in ESO, or use the native **Secrets Store CSI Driver**.

### B.8 Detection & Audit Services

| Service | What it does |
|---------|-------------|
| **CloudTrail** | Records every API call (management + data events). Ship to S3 + CloudWatch Logs. **Turn on in every account, every region.** |
| **Config** | Tracks resource configurations over time + compliance rules (e.g., "no public S3 buckets"). |
| **GuardDuty** | Threat detection (ML on CloudTrail, VPC Flow Logs, DNS logs). Detects crypto-mining, port scans, compromised credentials. |
| **Security Hub** | Aggregates findings from GuardDuty, Inspector, Macie, 3rd-parties. Compliance packs (CIS, PCI). |
| **Inspector** | Vulnerability scanning for EC2, ECR images, Lambda. |
| **Macie** | PII/sensitive-data discovery in S3. |
| **Detective** | Graph-based incident investigation. |
| **Audit Manager** | Evidence collection for compliance frameworks. |

### B.9 Perimeter Protection

| Service | Layer |
|---------|-------|
| **WAF** | L7 — OWASP managed rules, rate limits, bot control. Attach to ALB, CloudFront, API GW, AppSync. |
| **Shield Standard** | Free, auto-on DDoS protection at L3/4. |
| **Shield Advanced** | Paid (~$3k/mo). Cost protection, DRT access, L7 mitigations, advanced reports. |
| **Firewall Manager** | Central WAF/Shield/NACL policies across accounts. |
| **Network Firewall** | Managed stateful firewall for VPC ingress/egress (Suricata rules). |

### B.10 Encryption in Transit & at Rest

| Data state | Default options |
|------------|----------------|
| In-transit | TLS 1.2+ via ACM. HTTPS on ALB/CloudFront/API GW. Private CA via ACM PCA. |
| At rest (storage) | S3 SSE-S3/SSE-KMS/SSE-C/DSSE-KMS. EBS encryption-by-default. EFS encryption-by-default. |
| At rest (DB) | RDS storage encryption (KMS). DynamoDB always encrypted. |
| End-to-end app | Envelope encryption via KMS Data Keys; clients decrypt locally. |

**ACM:** Free public certs, auto-renewal. Attach to ALB/CF/API GW — no manual rotation. PCA for private CA.

### B.11 Organizations, SCPs, Control Tower

**AWS Organizations** = multi-account management (billing, OUs, SCPs, trust).

**Why multi-account?**
- Hard isolation (a compromised dev account can't touch prod).
- Separate billing.
- Per-account service quotas.

**Recommended landing zone:**
```
Root
├── Management (payer)          # billing, Orgs API, SSO
├── Log Archive                 # central CloudTrail/Config logs
├── Audit (Security)            # Security Hub delegated admin, GuardDuty
├── Shared Services             # central DNS, AD, golden AMIs
├── Workloads OU
│   ├── Prod
│   ├── Staging
│   └── Dev / Sandbox
└── Suspended OU                # for off-boarded accounts
```

**SCP** — denies or allows service/action at the account level. **Does not grant** by itself; it caps what IAM can grant. Classic guardrails:
- Deny use of regions other than approved ones.
- Deny deletion of CloudTrail.
- Require IMDSv2 on EC2.
- Deny attaching IGW (in workload accounts).

**Control Tower** — packaged landing zone (OUs + SCP guardrails + audit account + SSO). Opinionated, fast.

### B.12 Identity Center (SSO)

Single identity source → federated roles in each account.

Flow: User → Identity Center portal → pick account + permission set → STS AssumeRole → console/CLI.

Permission Set = templated role (name + policies) that Identity Center provisions into each account.

**CLI:** `aws configure sso` → named profiles → `aws sts get-caller-identity` confirms.

### B.13 IAM/Security Troubleshooting Scenarios

1. **"AccessDenied" even though my policy allows.** Check (a) explicit Deny somewhere (identity, resource, SCP, boundary); (b) Condition keys not matching (MFA, IP); (c) wrong resource ARN; (d) typo in Action; (e) resource-based policy doesn't allow your principal.
2. **EKS pod can't access S3 despite IRSA configured.** ServiceAccount annotation + trust policy on role must match the OIDC provider URL exactly. Check with `aws sts get-caller-identity` from a debug pod.
3. **Role assumption works from CLI but not from Lambda.** Lambda's execution role is being used; `sts:AssumeRole` from inside Lambda needs both the execution role to allow `sts:AssumeRole` **and** the target role's trust policy to list the execution role.
4. **S3 bucket encrypted with KMS — user can list but can't GetObject.** Add `kms:Decrypt` on the CMK (key policy + IAM). S3 permission alone isn't enough for SSE-KMS objects.
5. **CloudTrail is "enabled" but I don't see the event.** Data events (S3 object-level, Lambda invocations, DynamoDB item-level) are NOT captured by default — enable explicitly, charged separately.
6. **GuardDuty finding: "CryptoCurrency:EC2/BitcoinTool.B!DNS"** → likely compromised IAM credentials on an EC2. Rotate keys, check IMDSv2, look at CloudTrail `GetCallerIdentity` from unusual IPs.
7. **"iam:PassRole" denied on launch template.** Passing a role to a service (EC2, ECS, Lambda) requires the launching principal to have `iam:PassRole` on that role's ARN. Common CI/CD fail.
8. **Confused deputy — 3rd party vendor accidentally touched the wrong account.** Missing External ID on the trust policy. Add it.
9. **SCP blocks a new feature.** SCPs with "only allow these actions" patterns break when AWS adds a new API. Prefer Deny-lists for agility.
10. **Permissions boundary not working.** Common: boundary doesn't include `iam:*` actions, so the user can't create resources the identity policy otherwise allows.

### B.14 IAM/Security Interview Q&A

1. **What is the difference between IAM users and roles?**
   > Users have long-lived credentials (or console password). Roles have **no credentials** — they're assumed, yielding temporary STS creds. Prefer roles for everything except break-glass humans.

2. **Walk me through policy evaluation.**
   > Explicit Deny → Deny. Else SCP must allow. Else one of identity / resource policy must allow; boundary + session must allow if present. Else implicit Deny.

3. **How does IRSA work in EKS?**
   > EKS exposes an OIDC provider per cluster. Create IAM role with trust policy referencing that OIDC URL and a specific ServiceAccount. Annotate the ServiceAccount with the role ARN. The pod's projected token is exchanged via `sts:AssumeRoleWithWebIdentity` → temporary creds in env vars.

4. **What's IMDSv2 and why does it matter?**
   > Instance Metadata Service v2 requires a session token (PUT→GET pattern), hardening against SSRF attacks that exploited v1's simple GET. Required for modern security.

5. **How do you rotate an RDS master password?**
   > Secrets Manager with managed rotation calls a Lambda that generates a new password, updates RDS, updates the secret. Apps read the current version and retry on failure.

6. **What's envelope encryption?**
   > Data encrypted with a Data Encryption Key (DEK), DEK encrypted with a Customer Master Key (CMK) in KMS. Scales because CMK isn't used on the data directly; DEKs are.

7. **Resource policy vs identity policy — when to use each?**
   > Resource policies are mandatory for: cross-account, KMS key access, S3/SQS/SNS where the resource owner wants control. Identity policies for: everything else, centralized permission management.

8. **What's a Service-Linked Role?**
   > A role created and owned by an AWS service (e.g., `AWSServiceRoleForECS`). You can't edit its trust policy. Exists so services can act on your account's resources.

9. **Describe cross-account S3 access.**
   > Option 1: Bucket policy in A grants principals in B; B's IAM also allows it. Option 2: S3 ACL grant to canonical ID (old, avoid). Option 3: Access Point with cross-account policy.

10. **What's a VPC Endpoint policy used for — security-wise?**
    > Restricts which resources/APIs can be called through that endpoint. Example: gateway endpoint to S3 allowing only `arn:aws:s3:::my-company-*` buckets. Prevents data exfiltration to third-party buckets.

11. **Difference between Shield Standard and Advanced?**
    > Standard: free, L3/4 automatic. Advanced: ~$3k/mo, L7 protection, cost-attack protection, DDoS Response Team (DRT), historical reports.

12. **What is an SCP?**
    > Service Control Policy — Organization-level guardrail at the account boundary. Caps what IAM in that account can grant. Doesn't itself grant permissions.

13. **Why should you never use the root user?**
    > Root has unrestricted, ungovernable access (bypasses SCPs, IAM). Compromise = account takeover. Use IAM Identity Center + roles; lock away root creds + hardware MFA.

14. **How do you give a 3rd-party vendor least-privilege access?**
    > Create a role in your account with the minimum policy they need. Trust policy allows their account as principal + `sts:ExternalId` condition with a unique ID you share only with them. Never share IAM user keys.

15. **STS token expiry — how do you handle long-running jobs?**
    > Default 1h (role), up to 12h. Use a refreshing credential provider (AWS SDKs handle this with `AssumeRoleProvider`), or for scripts, re-assume periodically.

16. **What's the difference between KMS Grant and Key Policy?**
    > Key policy is static IAM-like. Grants are programmatic, time-limited, per-context (encryption context) — used when another AWS service needs to use your CMK on your behalf (EBS volume encryption, for instance).

17. **CloudTrail event goes to S3 but how do you alert on it?**
    > CloudTrail → CloudWatch Logs → metric filter (pattern match on API event name) → CloudWatch alarm → SNS → Slack/email. Or EventBridge rule directly on CloudTrail events.

18. **How do you centralize security findings across accounts?**
    > Security Hub with delegated admin in a dedicated audit account. GuardDuty, Inspector, Macie, Config all feed it. Single pane for multi-account.

19. **What is federation, and how does it differ from IAM users?**
    > Federation = users authenticate in an external IdP (Okta, Google, AD, Cognito) then assume an IAM role. No IAM user per human. Centralized lifecycle (offboarding in IdP revokes access).

20. **Your CI/CD is using long-lived AWS keys. How do you migrate to OIDC?**
    > In CI provider (GitHub Actions, GitLab), enable OIDC. Create an IAM role with trust policy referencing the OIDC provider + condition on repo/branch. CI job calls `AssumeRoleWithWebIdentity`. Delete the IAM user keys.

---

## Part C — Databases

### C.1 Service Map

| Service | Type | Best at |
|---------|------|---------|
| **RDS** | Managed relational (Postgres, MySQL, MariaDB, Oracle, SQL Server) | Lift-and-shift from self-managed DBs |
| **Aurora** | AWS-built MySQL/Postgres compatible | Cloud-native RDBMS with better HA, throughput, autoscaling |
| **DynamoDB** | Managed NoSQL (key-value + document) | Massive scale, single-digit ms latency, fully serverless |
| **ElastiCache** | Managed Redis / Memcached | Caching, session store, pub/sub |
| **Redshift** | Columnar MPP data warehouse | Analytical queries, PB-scale |
| **DocumentDB** | Managed MongoDB-compatible | Mongo workloads on AWS |
| **Neptune** | Managed graph DB | Social graphs, fraud detection |
| **Keyspaces** | Managed Cassandra | Cassandra users wanting managed |
| **Timestream** | Managed time-series | IoT, metrics |
| **QLDB** | Immutable ledger | Audit trails, financial ledgers |
| **OpenSearch** | Managed Elasticsearch fork | Search, log analytics |

### C.2 RDS Deep Dive

**Architecture:**
- Single-AZ: 1 instance. SLA: ~99.5%. Downtime during maintenance/failure.
- **Multi-AZ (standby)**: synchronous replica in another AZ, automatic failover (60–120s). SLA: 99.95%.
- **Multi-AZ DB cluster (new)**: 1 writer + 2 readable standbys, semi-sync, faster failover (~35s), readable.
- **Read replicas**: async, up to 15 (Aurora), cross-region supported. Eventual consistency.

**Engines & features:**
| Engine | Version freshness | Special |
|--------|------------------|---------|
| Postgres | Near-upstream | Large ecosystem, extensions (PostGIS, pg_stat_statements) |
| MySQL | 5.7 / 8.0 | Binlog for replication |
| MariaDB | 10.x | Light alternative to MySQL |
| Oracle / SQL Server | BYOL or Licence-Included | Enterprise workloads |

**Operational controls:**
- **Parameter groups** = my.cnf / postgresql.conf. DB-level settings. Some require reboot.
- **Option groups** = features (e.g., SQL Server SSRS, MySQL MEMCACHED).
- **Automated backups** — daily snapshot + 5-min continuous WAL → **Point-in-time recovery (PITR)** within backup window (7–35 days).
- **Manual snapshots** — retained until you delete.
- **Encryption** — storage, snapshots, replicas all encrypted with the same KMS key chain. Can't un-encrypt an instance; snapshot + restore with encryption.
- **Performance Insights** — visualize DB load by wait state, top SQL.
- **Enhanced Monitoring** — 1–60s OS-level metrics (CPU, memory, disk).

**Scaling:**
- Vertical: change instance class (requires restart, ~5 min).
- Storage autoscaling: grows GP2/GP3 up to a ceiling.
- Read scaling: read replicas with app-side routing.

### C.3 Aurora Deep Dive

- **Shared storage layer** — 6 copies of data across 3 AZs (4-of-6 writes, 3-of-6 reads).
- **Up to 15 read replicas**, all sharing the same storage — no replica lag from WAL shipping.
- **Faster failover** (~30s).
- **Aurora Serverless v2** — auto-scales ACUs in seconds by workload.
- **Global Database** — writer in primary region, async storage-level replication to up to 5 secondary regions (<1s lag). Fast promote for DR.
- **Backtrack** (MySQL) — "rewind" the DB in place without restore.
- **Parallel Query** — push WHERE/aggregation into storage layer.

### C.4 DynamoDB Deep Dive

**Data model:** Tables → Items → Attributes. **Partition Key** (mandatory) + optional **Sort Key** → "composite primary key." Attributes are schemaless.

**Capacity modes:**
| Mode | Billing | When |
|------|---------|------|
| **Provisioned** | RCU/WCU per second | Predictable traffic; cheaper at scale; Auto Scaling supported |
| **On-Demand** | Per-request | Spiky/unknown traffic; pay more per req but no capacity management |

**Indexes:**
| Index | Keys | Consistency | Scope |
|-------|------|-------------|-------|
| **GSI** | Any PK/SK | Eventually consistent | Up to 20 per table; own capacity |
| **LSI** | Same PK, different SK | Strongly consistent option | Must be defined at table creation; max 5 |

**Consistency:**
- **Eventually consistent** (default, cheaper, 2x reads for the RCU).
- **Strongly consistent** — `ConsistentRead=true`. Not supported on GSI.

**Streams + Lambda** = change data capture → trigger downstream.

**Global Tables** — multi-region active-active, last-writer-wins.

**DAX** — DynamoDB Accelerator — in-memory cache (microsecond reads).

**Transactions** — ACID across up to 100 items, 2x cost.

**Hot partition** — 3000 RCU / 1000 WCU per partition ceiling. Fix: better key distribution (suffix, composite), or on-demand.

### C.5 ElastiCache

| | **Redis** | **Memcached** |
|---|---|---|
| Data structures | Strings, lists, sets, hashes, sorted sets, streams, pub/sub | Strings only |
| Persistence | RDB snapshots, AOF | None |
| Replication | Primary + replicas, auto-failover (MemoryDB/Redis Cluster) | None |
| TLS / AUTH | Yes | No (use Redis) |
| Clustering | Redis Cluster (sharded) | Consistent hashing at client |
| Use | Cache + pub/sub + queues + leaderboards | Simple cache |

**MemoryDB for Redis** — Redis-compatible, but durable (multi-AZ transaction log) — OK as primary DB.

### C.6 Redshift

- Columnar + MPP. Query PB with SQL.
- **RA3 nodes** — compute + managed storage (S3-backed, scales independently).
- **Spectrum** — query S3 directly via external tables (like Athena).
- **Distribution styles:** EVEN, KEY, ALL, AUTO. Pick KEY for join-heavy.
- **Sort keys:** compound vs interleaved. Keeps data physically ordered.
- **Concurrency Scaling** — bursts extra clusters for peak query load.
- **Workload Management (WLM)** — query queues by user/group.

### C.7 Migration: DMS & SCT

- **DMS (Database Migration Service)** — source → target replication, homogeneous or heterogeneous (Oracle → Aurora Postgres).
- **SCT (Schema Conversion Tool)** — converts schema + stored procs.
- **CDC (Change Data Capture)** — initial load + continuous replication for cut-over.

### C.8 Backup, Restore & DR

| Approach | RPO | RTO | Cost |
|----------|-----|-----|------|
| **Backup & restore** (snapshots) | Hours | Hours | Low |
| **Pilot light** (DB replicating, app off) | Minutes | Minutes | Medium |
| **Warm standby** (scaled-down replica running) | Seconds | Minutes | Medium-High |
| **Multi-site active/active** (Global Tables, Aurora Global Writer Forwarding) | Near-zero | Near-zero | Highest |

### C.9 Database Interview Q&A

1. **RDS Multi-AZ vs Read Replica — difference?**
   > Multi-AZ = synchronous standby for HA, not readable. Read replica = async, readable, for scaling reads. Some engines let you promote a read replica to primary.

2. **What does Aurora do differently from RDS?**
   > Storage is decoupled — 6-way replicated across 3 AZs. Replicas share it, so lag is sub-10ms. Failover is ~30s. Throughput is 5x MySQL, 3x Postgres at comparable cost.

3. **Why is DynamoDB "hot partition" a problem?**
   > Data is sharded by partition key hash. A key that all traffic funnels into exceeds the per-partition RCU/WCU, throttling. Fix: spread keys, use random suffixes, or on-demand.

4. **LSI vs GSI?**
   > LSI: same PK, alternate SK, strongly consistent, defined at creation, counts against table's 10GB per-partition limit. GSI: any attributes, own capacity, eventually consistent, can be added later.

5. **How do you achieve strongly-consistent reads on DynamoDB?**
   > `ConsistentRead=true` on GetItem/Query — costs 2x RCU. Not available on GSI; GSIs are always eventually consistent.

6. **Explain Aurora Global Database.**
   > Primary region + up to 5 secondary regions. Storage-level async replication with <1s lag and <1min RPO. Manual promotion, fast failover in ~1 min. Supports headless secondaries.

7. **When would you pick Redshift over Athena?**
   > Predictable high-concurrency analytical workloads that benefit from pre-loaded data + MPP cluster resources. Athena for ad-hoc, infrequent queries directly on S3, pay-per-query.

8. **Your RDS is at 95% CPU — diagnosis steps.**
   > Performance Insights → top wait events + top SQL → explain analyze → missing index, lock contention, N+1 query, or just genuine load → add read replica / scale up / fix query.

9. **Your Postgres RDS replication lag is growing. Why?**
   > Large writes on primary (bulk import), long transactions holding WAL, replica under-provisioned, replication slot blocked. Check `pg_stat_replication`.

10. **DynamoDB auto-scaling is on, but you still hit `ProvisionedThroughputExceededException`. Why?**
    > Scaling isn't instantaneous. Target utilization default 70%, cooldowns apply. Spiky traffic scales slower than On-Demand. Options: raise floor, switch to on-demand, add DAX.

11. **How do you enforce encryption-at-rest on all new RDS in an account?**
    > Config rule "rds-storage-encrypted" flags non-compliant. SCP can deny `rds:CreateDBInstance` unless `StorageEncrypted=true`. Launch templates / Terraform defaults.

12. **DynamoDB transaction limits?**
    > Up to 100 items and 4 MB total across tables. 2× WCU/RCU cost. All-or-nothing. Scoped to a single region (not Global Tables-atomic).

13. **What is Aurora Serverless v2 useful for?**
    > Workloads with variable load (dev/staging, bursty SaaS tenants). Scales ACUs in seconds without a proxy — use it as a drop-in Aurora cluster.

14. **How do you do blue/green for a DB schema change?**
    > **RDS Blue/Green Deployments** clone the DB, apply schema changes on green, replicate primary → green, then switchover (~1 min downtime). Or manual: read replica, promote, switch endpoint.

15. **DynamoDB cost blowing up — first things to investigate.**
    > Scans (avoid — use Query), missing indexes (full scans fall back), GSI overprovisioning, TTL not configured so old data grows, on-demand on a steady workload (move to provisioned), hot partitions amplifying capacity.

---

## Part D — Storage

### D.1 S3 (Simple Storage Service)

**Object store:** unlimited objects, up to 5 TB each. 99.999999999% (11-nines) durability, 99.99% availability (Standard).

**Storage classes:**

| Class | Use | First-byte | Min charge period |
|-------|-----|-----------|--------------------|
| **Standard** | Hot data | ms | — |
| **Intelligent-Tiering** | Unknown/changing access pattern | ms (frequent tier) | 30d |
| **Standard-IA** | Infrequent access | ms | 30d |
| **One Zone-IA** | Reproducible, single AZ OK | ms | 30d |
| **Glacier Instant Retrieval** | Archive with millisecond reads | ms | 90d |
| **Glacier Flexible Retrieval** | Archive, retrieval in minutes–hours | minutes/hours | 90d |
| **Glacier Deep Archive** | Compliance archive, cheapest | 12h | 180d |

**Lifecycle rules** move objects between classes and expire them.

**Versioning** — protects against overwrites/deletes. A delete becomes a "delete marker," original still retrievable.

**Object Lock** — WORM (Write-Once-Read-Many) for compliance. Governance (admins can override) or Compliance (nobody, even root, during retention) modes.

**Encryption:**
| Mode | Keys |
|------|------|
| SSE-S3 | S3-managed |
| SSE-KMS | Customer CMK |
| SSE-C | Customer-provided key per request |
| DSSE-KMS | Double-layer, FIPS contexts |
| Client-side | Encrypted before upload |

**Access control (modern):**
- **Block Public Access** — account + bucket-level. **Turn on everywhere by default.**
- **Bucket policy** (resource policy).
- **Access Points** — named endpoints with their own policy; great per-team or per-workload.
- **Multi-region Access Point** — single global endpoint, fails over.
- **Object Ownership** — "Bucket owner enforced" disables ACLs entirely (recommended).

**Performance:**
- No partition naming hack needed anymore (3,500 PUT / 5,500 GET per prefix auto-scales).
- Multipart upload for >100 MB (required >5 GB).
- **Transfer Acceleration** — via CloudFront edges.
- **S3 Select** — SQL on a single object (CSV/JSON/Parquet).

**Cost traps:**
- Cross-region data transfer.
- `LIST` + `GET` on Glacier classes incur retrieval fees.
- IA classes have 128 KB minimum size per object for billing.
- Transfer-out to internet.

**Notification & events:** S3 Event Notifications → SNS/SQS/Lambda/EventBridge. Great ETL trigger pattern.

### D.2 EBS (Elastic Block Store)

Block storage attached to one EC2 at a time (except `io2 Block Express` multi-attach).

| Type | Use | Perf |
|------|-----|------|
| **gp3** | General purpose, **default** | Baseline 3000 IOPS / 125 MB/s; pay to increase |
| **gp2** | Legacy general | Performance tied to size |
| **io2 / io2 Block Express** | High IOPS, mission critical | Up to 256k IOPS, sub-ms |
| **st1** | Big sequential (logs, data lake on EC2) | Throughput-optimized HDD |
| **sc1** | Cold HDD | Cheapest |

**Snapshots:** incremental to S3 (internal). Copy across regions. Fast Snapshot Restore (FSR) warms blocks for predictable perf after restore.

**Encryption:** Enable "encryption by default" per region → all new volumes encrypted with default/custom CMK.

### D.3 EFS (Elastic File System)

**NFSv4 network file system** shared across EC2/ECS/EKS.

- **Performance modes:** General Purpose (default) / Max I/O (higher parallelism, higher latency).
- **Throughput modes:** Bursting (based on size) / Provisioned / Elastic.
- **Lifecycle management** → IA + Archive tiers for rarely-accessed files.
- **Access Points** — per-app POSIX uid/gid + root path isolation.

**Cost:** more $/GB than S3 or EBS. Use only when you need POSIX + sharing.

### D.4 FSx Family

| Variant | For |
|---------|-----|
| **FSx for Windows** | SMB, AD-joined Windows workloads |
| **FSx for Lustre** | HPC, ML training, with S3 link |
| **FSx for NetApp ONTAP** | Enterprise NetApp features (SnapMirror, etc.) |
| **FSx for OpenZFS** | ZFS snapshots/clones |

### D.5 Storage Gateway

On-prem hybrid:
- **S3 File Gateway** — NFS/SMB → S3 objects.
- **Volume Gateway** — iSCSI → EBS snapshots.
- **Tape Gateway** — virtual tape → Glacier.

### D.6 Backup Services

- **AWS Backup** — central policy-based backups across EBS, RDS, DynamoDB, EFS, FSx, Storage Gateway. Cross-region, cross-account.
- **DataSync** — bulk migration/sync between on-prem NFS/SMB/HDFS and S3/EFS/FSx.

### D.7 Storage Interview Q&A

1. **Which S3 storage class for logs you rarely read but must keep 1 year?**
   > Lifecycle rule: Standard → IA (after 30d) → Glacier Flexible (after 90d) → expire at 1y. Or Intelligent-Tiering if access is unpredictable.

2. **Your S3 bucket is accidentally public. Steps to remediate.**
   > Enable Block Public Access at account + bucket. Review bucket policy + ACLs. Enable "Bucket owner enforced" to disable ACLs. Scan CloudTrail for reads. Enable Access Analyzer.

3. **How does S3 guarantee 11 nines of durability?**
   > Each object replicated across ≥3 AZs with checksums; continuous integrity verification; auto-repair.

4. **What's the difference between SSE-KMS and SSE-S3?**
   > SSE-S3 uses an S3-managed AES-256 key (no KMS cost, no audit trail). SSE-KMS uses your CMK — audit via CloudTrail, access control via KMS policy — but KMS API calls cost and add latency.

5. **S3 Access Points vs bucket policies?**
   > Access Points are per-application DNS entries with their own policy scoped to a prefix. Cleaner than cramming many conditions into a single bucket policy at scale.

6. **EBS volume full, need to expand. Any downtime?**
   > `ModifyVolume` API — online resize. Then filesystem grow (`resize2fs` / `xfs_growfs`) without unmount. Cooldown of ~6h before next modification.

7. **When would you pick EFS over S3?**
   > Need POSIX semantics (atomic rename, byte-level updates, locking), multi-host read/write, legacy app expects a mount point.

8. **How do you migrate 500 TB from on-prem to S3?**
   > DataSync if you have >1 Gbps clean pipe. Snowball Edge if bandwidth-constrained. Snowmobile (truck!) for petabytes in remote locations.

9. **S3 object-level permissions (ACL) vs bucket policy — which wins?**
   > Union: access granted if *any* evaluates to Allow, unless explicit Deny. Best practice: disable ACLs ("Bucket owner enforced"), use policies only.

10. **Which EBS type for a boot volume on a general-purpose app?**
    > gp3 — cheaper than gp2, baseline IOPS independent of size, tunable.

---

## Part E — Compute

### E.1 EC2 Basics

**Instance families** (letters = category):
- **M** — general purpose (M7g = Graviton3 ARM)
- **C** — compute optimized
- **R** — memory optimized
- **X / z** — extra memory
- **I / D / Im** — storage/NVMe
- **P / G / Inf / Trn** — GPU/ML accelerator
- **T** — burstable (credits) — cheap for bursty, small workloads
- **A / Graviton (g suffix)** — ARM (cheaper/$perf on compatible workloads)

**Purchasing options:**

| Type | Discount | Commit | Use |
|------|----------|--------|-----|
| **On-Demand** | — | None | Spikes, dev |
| **Reserved Instance** | Up to 72% | 1 or 3 yr | Stable baseline |
| **Savings Plans** | Up to 72% | 1 or 3 yr | Like RI but flexible across family/region |
| **Spot** | Up to 90% | Can be reclaimed in 2 min | Stateless, fault-tolerant workloads |
| **Dedicated Host / Instance** | — | License compliance | BYOL, regulatory |
| **Capacity Reservations** | — | Reserve capacity (not pricing) | Guarantee instances for events/DR |

**Placement groups:**
- **Cluster** — same rack, 10 Gbps between nodes. HPC.
- **Spread** — across distinct racks/AZ. Small critical clusters (Kafka, Zookeeper).
- **Partition** — racks grouped into partitions, one per partition fails independently. Hadoop/Cassandra.

**Auto Scaling Group (ASG):**
- Launch template (desired AMI, instance types, user data).
- Min/Max/Desired capacity.
- Scaling policies: target tracking, step, scheduled.
- Health checks: EC2 (default) or ELB (preferred).
- **Lifecycle hooks** — let you run actions at launch/terminate (drain traffic, backup).

**User data** — boot-time script (cloud-init). Rendered from Terraform template. `cloud-init-output.log` for debugging.

**IMDSv2** — required pattern for metadata access.

### E.2 Elastic Beanstalk / Lightsail

- **Beanstalk** — PaaS-like: push code, AWS provisions EC2 + ALB + ASG. Good for simple web apps; heavy underneath (exposes underlying resources).
- **Lightsail** — ultra-simple VPS pricing (bundled bandwidth). Not for production at scale.

### E.3 Lambda

**Execution model:** function + event → Lambda provisions an execution environment (container), runs, tears down (or caches "warm").

| Concept | Detail |
|---------|--------|
| **Cold start** | First invocation after idle — runtime init. Reduce with provisioned concurrency, smaller deps, SnapStart (Java). |
| **Concurrency** | Reserved (dedicated pool + cap) vs provisioned (pre-warmed). Account limit 1000 default. |
| **Timeouts** | Max 15 min. For longer, use Step Functions / ECS. |
| **Memory** | 128 MB–10 GB. CPU scales proportionally to memory. |
| **Runtimes** | Node.js, Python, Java, .NET, Go, Ruby, custom via container image. |
| **Event sources** | API Gateway, S3, SNS, SQS, EventBridge, DDB Streams, Kinesis, ALB, Step Functions… |
| **Destinations** | Async invocations route success/failure to SQS/SNS/EventBridge/Lambda. |
| **Layers** | Shared code/libs across functions. |
| **VPC access** | Opt-in. Cold starts can increase. Needs subnets + SG. |
| **Dead Letter Queue** | SQS/SNS for failed async events. |

**Pricing:** number of requests + GB-seconds (memory × duration). Very cheap for low volumes.

### E.4 Auto Scaling & Load Across Compute

Target-tracking on CPU, ALB request count, or custom metric — simplest and usually enough. Step policies when you need asymmetric scale-up vs scale-down. Predictive scaling uses ML.

---

## Part F — Containers & Serverless

### F.1 ECR (Elastic Container Registry)

- Private Docker/OCI registries per account.
- **Image scanning** (Basic — Clair; Enhanced — Inspector).
- **Lifecycle policies** to expire old images (avoid bill creep).
- **Cross-region replication**, cross-account pull-through.
- **Pull-through cache** rules mirror Docker Hub / quay.io images on demand.

### F.2 ECS (Elastic Container Service)

| Launch type | Who runs it |
|-------------|-------------|
| **EC2** | You manage the EC2 hosts |
| **Fargate** | AWS runs containers serverlessly — no hosts to manage |

**Abstractions:**
- **Task Definition** — container spec (image, CPU, mem, env, volumes).
- **Service** — keeps N copies of a Task Definition running; can integrate with ALB target group.
- **Cluster** — logical grouping.

**Networking modes (EC2 launch):** `awsvpc` (recommended — each task gets its own ENI; SG scoping), `bridge`, `host`.

### F.3 EKS (Elastic Kubernetes Service)

Managed control plane (API server, etcd, scheduler) — you manage worker nodes (EC2, managed node groups, or Fargate profiles).

**Deep concepts (mapped from Module 5):**

| K8s | AWS-native |
|-----|-----------|
| Cluster networking | VPC CNI plugin (pod IP = ENI secondary IP from VPC CIDR — no overlay) |
| Ingress | AWS Load Balancer Controller → ALB/NLB |
| PersistentVolume | EBS CSI driver / EFS CSI driver / FSx CSI |
| Service → LoadBalancer | NLB (by default via AWS LB Controller) |
| Cluster autoscaler | **Karpenter** (next-gen) or classic CA on ASGs |
| ServiceAccount → IAM | **IRSA** (OIDC-federated roles) |
| Secrets | External Secrets Operator w/ AWS SM/Parameter Store, or **Secrets Store CSI Driver** |
| Logs | Fluent Bit → CloudWatch Logs / OpenSearch / Kinesis Firehose |

**Upgrade path:** plan K8s version bumps quarterly; extended support available for +1 year at extra cost.

### F.4 Fargate (both ECS and EKS)

Per-vCPU + per-GB pricing, no nodes. Ideal for:
- Variable workloads.
- Security isolation (per-task kernel).
- Small teams that don't want to patch nodes.

Tradeoffs: higher $/vCPU than EC2 at steady-state; no DaemonSets in EKS-Fargate; no GPUs; slower pod start.

### F.5 App Runner

Fully managed container web app service — `code` or `image` → URL, with autoscaling + TLS. No infra to run. Simpler than ECS/EKS for a single service.

---

## Part G — Messaging & Integration

| Service | Pattern |
|---------|---------|
| **SQS Standard** | At-least-once, nearly unlimited TPS, best-effort order |
| **SQS FIFO** | Exactly-once, ordered within MessageGroupId, 3000 msg/s (batching) |
| **SNS** | Pub/Sub fan-out to Lambda/SQS/HTTP/Email/SMS; FIFO variant |
| **EventBridge** | Event bus with rules/targets; schema registry; SaaS partner events; cron scheduling |
| **Step Functions** | Serverless orchestration (state machines); retries, parallel, wait, choice; Express vs Standard workflows |
| **API Gateway** | REST (full featured), HTTP (lighter, cheaper), WebSocket. Auth via IAM/Cognito/Lambda authorizer |
| **AppSync** | Managed GraphQL (DynamoDB/RDS/Lambda resolvers) |
| **MQ** | Managed RabbitMQ / ActiveMQ (lift-and-shift JMS) |
| **MSK** | Managed Kafka |
| **Kinesis Data Streams** | Ordered, replayable streams. Shards = units of capacity |
| **Kinesis Firehose** | Managed delivery to S3/Redshift/OpenSearch, no shards |
| **Kinesis Analytics** | SQL/Flink on streams |

**Idempotency** is the caller's problem in every messaging system. Store a dedup token in DynamoDB if the API is non-idempotent.

---

## Part H — Observability on AWS

| Signal | Native tool | OSS alt (what we use) |
|--------|-------------|------------------------|
| Metrics | CloudWatch Metrics | Prometheus |
| Logs | CloudWatch Logs / OpenSearch | Loki |
| Dashboards | CloudWatch Dashboards | Grafana |
| Tracing | X-Ray | Jaeger / Tempo |
| Alerts | CloudWatch Alarms → SNS | Alertmanager → Slack |
| Ingestion | CloudWatch Agent / Fluent Bit | Promtail / OTel Collector |
| RUM | CloudWatch RUM | — |
| Synthetics | CloudWatch Synthetics | Blackbox exporter |

**CloudWatch Logs Insights** — SQL-ish query language:
```
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

**EMF (Embedded Metric Format)** — log structured JSON that CloudWatch auto-extracts as metrics (cheaper than PutMetric for high cardinality).

**Amazon Managed Service for Prometheus / Grafana (AMP/AMG)** — managed OSS. A common middle ground between CloudWatch and running your own stack.

**Cross-account observability** — source accounts send logs/metrics to a monitoring account via Observability Access Manager.

---

## Part I — Cost, Governance & Organizations

### I.1 Cost

- **Cost Explorer** — visualize spend, forecast, by service/account/tag.
- **Budgets** — alert when actual/forecast crosses thresholds.
- **Cost Anomaly Detection** — ML alerts on unusual spend.
- **Compute Optimizer** — right-sizing recommendations (EC2, ASG, Lambda, EBS).
- **Trusted Advisor** — checks (idle resources, underutilized RIs, security).

### I.2 Tagging Strategy

At minimum: `Environment`, `Owner`, `CostCenter`, `Application`. Enforce with SCP (`aws:RequestTag/Environment`) and Config rules. Tag Editor for bulk updates.

### I.3 Savings Plans vs RIs vs Spot

- **Compute Savings Plan** — 1/3yr commit $/hr; applies across EC2/Fargate/Lambda, any region, any family.
- **EC2 Instance SP** — family-specific, slightly deeper discount.
- **Reserved Instances** — legacy; Savings Plans preferred.
- **Spot** — up to 90% off; 2-min interruption notice; great for CI runners, batch, stateless autoscaling groups.

### I.4 AWS Organizations Deep Dive (continued)

- **Consolidated billing** — aggregate invoices, shared volume discounts, pooled RI/SP savings.
- **Delegated admin** — spread operational ownership (Security Hub admin in audit account, CloudFormation StackSets admin, etc.) without handing out root.
- **StackSets** — deploy CloudFormation stacks across many accounts/regions from the mgmt account.

---

## Cross-Cutting Troubleshooting Scenarios

1. **The app is slow and CloudWatch shows ALB `TargetResponseTime` spiking.** → is the issue at the target (check container CPU/mem/X-Ray), or at the DB (RDS Performance Insights), or in a downstream API (circuit breaker showing timeouts)? Use the RED method: Rate/Errors/Duration per dependency.
2. **IAM role policy update propagated slowly.** IAM is **eventually consistent**. New roles/policies can take seconds-to-minutes to fully replicate across regions/services. Retry or use STS with immediate scope.
3. **S3 cross-account access failing after a policy change.** Double-check: bucket policy allows principal, principal's IAM allows it, KMS key policy allows it (if SSE-KMS), Block Public Access isn't denying at account/bucket level, Object Ownership is "Bucket owner enforced."
4. **EKS pod stuck in `Pending` with "Insufficient pods".** VPC CNI ENI quota hit — instance type's max pods exceeded. Enable prefix delegation (`WARM_PREFIX_TARGET=1`) or use Karpenter to pick a bigger type.
5. **CloudFront returns 403 on S3 origin.** OAC not configured, or bucket policy doesn't allow the CloudFront service principal, or Block Public Access is still blocking the policy.
6. **"Rate exceeded" on Terraform apply.** AWS API rate-limiting. Add `provider` `max_retries`, reduce parallelism (`-parallelism=5`), split stacks.
7. **Lambda inside a VPC has massive cold starts.** Historically ENI attach was slow — AWS changed this (Hyperplane ENIs 2019+), but misconfiguration (small subnets with no free IPs) still causes failures. Add capacity or use provisioned concurrency.
8. **Secrets Manager rotation broke the app.** Apps cache credentials too long. Use the SDK cache with a small TTL, or add a reconnect-on-auth-error retry. RDS Proxy also handles rotation without app awareness.

---

## STAR Stories

### Story 1 — The $4K NAT Gateway Bill

**Situation.** A staging EKS cluster racked up $4k in NAT GW data-processing charges in one month.

**Task.** Diagnose and cut the bill to reasonable levels without blocking developer workflows.

**Action.** CloudWatch metrics on the NAT GW showed `BytesOutToDestination` dominated by S3 endpoints. Pulled a sample of Flow Logs into Athena; top destinations were S3 + ECR image pulls. Added an **S3 Gateway Endpoint** (free) and **ECR Interface Endpoints** (Docker API + token + DKR) with a VPC endpoint policy scoping to our accounts' repos. Re-routed private subnets to the new endpoints.

**Result.** NAT GW data processing dropped 92% the next month. Total monthly spend fell by ~$3.7k. Added Cost Anomaly Detection + tag-based budgets so future spikes page the team. Generalized the pattern into a module for every new VPC.

### Story 2 — Confused Deputy Near-Miss

**Situation.** A vendor integration used a role with trust policy `{"Principal": {"AWS": "arn:aws:iam::VENDOR_ACCT:root"}}` and no External ID.

**Task.** The vendor was onboarding a new customer with the same role ARN template — risk of accidentally using their creds against our account.

**Action.** Rotated the trust policy to include `Condition.StringEquals.sts:ExternalId = "<unique-per-customer>"` shared only out-of-band with our account. Added `aws:SourceAccount` and `aws:SourceArn` conditions for services invoking the role. Generated a short Jira runbook for future vendor onboarding ("no role without External ID").

**Result.** Eliminated the confused-deputy exposure. All downstream vendor roles audited and 3 others fixed the same way. Made External ID enforcement an SCP-enforced rule across the org.

### Story 3 — S3 Public Bucket Drill

**Situation.** A weekly scan flagged an S3 bucket in dev as world-readable after a developer turned off Block Public Access for a temporary test.

**Task.** Contain the exposure, confirm no data left the bucket, and prevent recurrence.

**Action.** Re-enabled BPA at account **and** bucket level. Parsed CloudTrail data events + S3 server access logs for `GetObject` from external IPs in the exposure window — none found (bucket only had test fixtures). Enabled "Bucket owner enforced" on every bucket in the org to disable ACLs. Rolled out an SCP that denies `s3:PutAccountPublicAccessBlock` with `RestrictPublicBuckets=false`. Added AWS Config rule for continuous detection + Access Analyzer for proactive findings.

**Result.** Zero data leaked; MTTR ~15 min after initial alert. Locked door closed by guardrail: the SCP prevents the same misconfiguration in every account going forward. Drill converted into a gameday runbook.

### Story 4 — Cross-Account IRSA

**Situation.** Flask app on EKS in Account A needed to write to DynamoDB in Account B.

**Task.** Do this without long-lived keys or overly broad roles, with a clean audit trail.

**Action.** Account A: IRSA role trusted the cluster's OIDC provider for a specific ServiceAccount. That role had `sts:AssumeRole` permission on a target role in Account B. Account B: role with DynamoDB PutItem on the specific table, trust policy allowing the Account-A role ARN. Pod picks up IRSA creds via the projected token, then chains via `sts:AssumeRole` to Account B before writing.

**Result.** No static secrets anywhere. CloudTrail in both accounts shows the assume-role and PutItem with the pod's SA as the trail's `userIdentity`. Same pattern reused for two more app → data-account integrations.

---

## Production Hardening — Well-Architected Mapping

| Pillar | Key practices for this project, if deployed |
|--------|--------------------------------------------|
| **Operational Excellence** | Everything IaC (Terraform + Helm + ArgoCD). CloudWatch dashboards + synthetic probes. Runbooks. GitOps audit trail. |
| **Security** | Multi-account (Organizations + Control Tower). IAM Identity Center SSO. IRSA for EKS. KMS with CMK for all data. Secrets Manager with rotation. GuardDuty + Security Hub + Config. SCP guardrails. Block Public Access org-wide. CloudTrail to immutable S3 + Glue catalog. |
| **Reliability** | Multi-AZ RDS/Aurora. Multi-AZ NAT. ALB health checks + auto-scaling. Backups + AWS Backup policies. DR runbook (pilot light → warm standby). Chaos gameday. |
| **Performance** | Right-size via Compute Optimizer. Graviton where possible. DAX / ElastiCache for hot reads. CloudFront for static assets. |
| **Cost** | Savings Plans for steady-state. Spot for CI/stateless. VPC endpoints to kill NAT egress. S3 lifecycle + Intelligent-Tiering. Budgets + Cost Anomaly Detection. Required tags enforced via SCP. |
| **Sustainability** | Graviton, Spot, smaller regions closer to users, managed services that pack better than self-run. |

---

## Mapping This Project to AWS

| Module / component | Minikube (current) | AWS-native counterpart |
|--------------------|---------------------|------------------------|
| Flask + Postgres app | Deployments on minikube | ECS/Fargate or EKS + RDS/Aurora |
| Ingress | Minikube nginx | ALB via AWS Load Balancer Controller |
| Persistent storage | Minikube hostpath PVCs | EBS CSI / EFS CSI |
| Secrets | Vault + ESO | Secrets Manager + ESO (or Secrets Store CSI Driver) |
| CI pipeline | GitHub Actions self-hosted | Same, + OIDC to AWS + ECR push |
| Image registry | DockerHub | **ECR** with scanning + lifecycle |
| DNS | `/etc/hosts` | **Route 53 private hosted zone** |
| TLS | None in dev | **ACM** on ALB + CloudFront |
| Observability | Prometheus/Grafana/Loki | **AMP + AMG + CloudWatch Logs**, or keep OSS on EKS |
| Alerts | Alertmanager → Slack | Same, or CloudWatch Alarms → SNS → Slack |
| Cluster | Minikube 3-node | **EKS** + managed node groups + Karpenter |
| GitOps | ArgoCD | Same on EKS; optional AWS CodePipeline for CodeCommit source |
| Network CIDRs (terraform/) | 10.0.0.0/16 with tiered subnets | Ported as-is; add VPC endpoints, flow logs, NAT per AZ |
| IAM | K8s RBAC | **IRSA** bridging K8s SA → AWS IAM role |
| Compliance | Manual | Config + Security Hub + SCPs + CloudTrail org trail |

**Migration sequence if we had to deploy this for real:**
1. Land the accounts with Control Tower (Mgmt / Audit / LogArchive / Prod / Staging / Dev).
2. Provision core network (VPC + subnets + endpoints + TGW-ready) with Terraform — reuse `terraform/` as the base.
3. Push images to ECR from CI.
4. Stand up EKS with managed node groups + Karpenter; install AWS LB Controller, EBS CSI, External DNS, cert-manager, ESO (pointed at Secrets Manager).
5. Port Helm charts as-is (they're cloud-agnostic) — swap storage classes and Ingress classes.
6. Cut over DNS via Route 53 with weighted records; watch dashboards; roll back in one step if needed.

---

## Further Reading

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/)
- [AWS Security Reference Architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/)
- [EKS Best Practices Guides](https://aws.github.io/aws-eks-best-practices/)
- [Prescriptive Guidance — Patterns](https://aws.amazon.com/prescriptive-guidance/)
- [AWS Pricing Calculator](https://calculator.aws/)
