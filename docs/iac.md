# Module 4: Infrastructure as Code (Terraform & Ansible)

> **Goal:** Provision the AWS network + compute layer with **Terraform** (declarative IaC) and configure the resulting machines with **Ansible** (imperative configuration management).

> **Why this matters:** Clicking through cloud consoles doesn't scale. Every serious DevOps/SRE org provisions infra-as-code so it's reproducible, version-controlled, and reviewable. Terraform + Ansible is one of the most asked-about combos in interviews because it cleanly separates "what to create" from "what to configure."

> **Scope of this project:** We **wrote** the Terraform and Ansible code as a reference architecture but did **not deploy to AWS** (to avoid cloud costs). This doc is the deep-dive needed to understand, operate, and troubleshoot it in production.

---

## Table of Contents

1. [Why IaC](#why-iac)
2. [Terraform vs Ansible — When to Use What](#terraform-vs-ansible--when-to-use-what)
3. [Architecture](#architecture)
4. [Part A — Terraform Deep Dive](#part-a--terraform-deep-dive)
5. [Part B — Ansible Deep Dive](#part-b--ansible-deep-dive)
6. [Commands Reference](#commands-reference)
7. [Troubleshooting (Real-World Scenarios)](#troubleshooting-real-world-scenarios)
8. [Interview Q&A](#interview-qa)
9. [STAR Stories](#star-stories)
10. [Production Hardening](#production-hardening)
11. [Cloud Mapping](#cloud-mapping)

---

## Why IaC

| Without IaC | With IaC |
|-------------|----------|
| Click-ops in AWS console | Code in git, peer-reviewed |
| Snowflake servers — each one different | Identical environments dev/staging/prod |
| Hours to recreate after disaster | `terraform apply` to recreate |
| No audit trail | `git log` shows every change |
| Drift goes undetected | `terraform plan` detects drift |
| Costly mistakes (forgotten resources) | `terraform destroy` for clean teardown |

---

## Terraform vs Ansible — When to Use What

| Aspect | Terraform | Ansible |
|--------|-----------|---------|
| **Paradigm** | Declarative (you describe end state) | Imperative (you describe steps) |
| **Primary use** | Provision cloud infra (VPCs, EC2, RDS, ALB) | Configure existing machines (install packages, edit configs) |
| **State** | Maintains a state file (`terraform.tfstate`) | Stateless (each run inspects current state) |
| **Idempotency** | Yes — `apply` only changes what's drifted | Yes — modules check before doing |
| **Language** | HCL (Hashicorp Configuration Language) | YAML |
| **Agent** | None (uses cloud APIs) | None (SSH-based) |
| **Order** | Dependency graph auto-built | Sequential (you control order) |
| **Best at** | Building infrastructure | Configuring infrastructure |

**Common workflow:** Terraform creates the EC2 → Ansible installs Docker, K8s, monitoring agents on it. Don't try to make Terraform do config management or Ansible provision cloud — they fight each other.

---

## Architecture

```
┌────────────────── AWS Account ──────────────────────────────----───┐
│                                                                    │
│  ┌──────────────────────── VPC: 10.0.0.0/16 ───────────────---──┐  │
│  │                                                              │  │
│  │   AZ us-east-1a               AZ us-east-1b                  │  │
│  │  ┌──────────────────┐        ┌─────────────────-─┐           │  │
│  │  │ Public  10.0.0/24│        │ Public  10.0.10/24│           │  │
│  │  │  ┌───┐  ┌───────┐│        │ ┌───┐  ┌────────┐ │           │  │
│  │  │  │ALB│  │NAT-GW │◄────────┼─┤ALB│  │NAT-GW  │ │           │  │
│  │  │  │   │  │+ EIP  ││        │ │   │  │+ EIP   │ │           │  │
│  │  │  └───┘  └───────┘│        │ └───┘  └────────┘ │           │  │
│  │  └──────────────────┘        └───────────────-───┘           │  │
│  │                                                              │  │
│  │  ┌──────────────────┐        ┌────────────────-──┐           │  │
│  │  │ App     10.0.1/24│        │ App     10.0.11/24│           │  │
│  │  │   EC2 Bastion    │        │   EC2 Bastion -   │           │  │
│  │  └──────────────────┘        └───────────────-───┘           │  │
│  │                                                              │  │
│  │  ┌──────────────────┐        ┌──────────────-────┐           │  │
│  │  │ DB      10.0.2/24│        │ DB      10.0.12/24│           │  │
│  │  └──────────────────┘        └──────────────-────┘           │  │
│  │                                                              │  │
│  │  ┌──────────────────┐        ┌──────────────────┐            │  │
│  │  │ Dependent        │        │ Dependent       m│            │  │
│  │  │ Services 10.0.3/24        │ Services 10.0.13/24           │  │
│  │  └──────────────────┘        └──────────────────┘            │  │
│  │                                                              │  │
│  │  ┌──────────────────┐        ┌──────────────────┐            │  │
│  │  │ Observability    │        │ Observability    │            │  │
│  │  │         10.0.4/24│        │         10.0.14/24│           │  │
│  │  └──────────────────┘        └──────────────────┘            │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              │ Internet Gateway                    │
└──────────────────────────────┼─────────────────────────────────────┘
                               │
                          internet
```

**Subnet purpose by tier:**
| Subnet Type | Houses | Routing |
|-------------|--------|---------|
| Public | ALB, NAT GW, Bastion | IGW for inbound; egress via IGW |
| App | Application servers | Egress via NAT |
| DB | Databases (RDS) | No internet egress (isolated) |
| Dependent Services | Vault, etc. | Egress via NAT |
| Observability | Prometheus, Grafana | Egress via NAT |

---

## Part A — Terraform Deep Dive

### File Structure

```
terraform/
├── main.tf       # All resources: VPC, subnets, NAT, SGs, EC2, ALB
├── variables.tf  # Input variables with defaults
└── outputs.tf    # Outputs (IDs, IPs, ARNs) for downstream use
```

### Provider Block ([main.tf](../terraform/main.tf))

```hcl
terraform {
  required_version = ">=1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

**Why pin provider versions?** A breaking change in the AWS provider (`5.x → 6.x`) could change attribute names or default behavior. Pinning to `~>5.0` allows minor updates (5.1, 5.2) but blocks major (6.x).

### Resource Patterns We Use

#### 1. `for_each` over `count`

```hcl
resource "aws_subnet" "public" {
  for_each                = var.azs        # map keys = AZ names
  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.public
  availability_zone       = each.key
  map_public_ip_on_launch = true
  tags = { Name = "${var.project_name}-public-${each.key}" }
}
```

**Why `for_each` over `count`?**
| `count` | `for_each` |
|---------|-----------|
| Indexed by integer (`subnet[0]`, `subnet[1]`) | Indexed by key (`subnet["us-east-1a"]`) |
| Removing item shifts indexes → recreates | Removing item only affects that key |
| Use for true lists | Use for maps/sets (stable identity) |

If we used `count` and removed AZ `us-east-1a` from the map, all subnets would shift index → Terraform would destroy and recreate them. With `for_each`, only that key is removed.

#### 2. Implicit Dependency Graph

```hcl
resource "aws_subnet" "public" {
  vpc_id = aws_vpc.main.id  # ← dependency on VPC
}
```

Terraform reads the reference and builds a DAG. No need for explicit `depends_on` unless the dependency isn't in code (e.g., between resources via side-effects).

When to use **explicit** `depends_on`:

```hcl
resource "aws_nat_gateway" "main" {
  # ...
  depends_on = [aws_internet_gateway.main]   # NAT requires IGW for routing
}
```

#### 3. Outputs ([outputs.tf](../terraform/outputs.tf))

```hcl
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ssh_commands" {
  value     = [for i in aws_instance.api_server : "ssh -i ${var.key_name}.pem ubuntu@${i.public_ip}"]
  sensitive = true
}
```

`sensitive = true` — masks output in CLI; still visible in state file (state files contain everything sensitive).

#### 4. Variable Validation

```hcl
variable "my_ip" {
  description = "Your public IP for SSH access"
  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.my_ip))
    error_message = "my_ip must be a valid /32 CIDR, e.g., 203.0.113.25/32"
  }
}
```

Catches bad inputs before `apply`. Saves a failed `apply` that would partially provision.

### State Management

The **state file** (`terraform.tfstate`) is the source of truth for what Terraform knows it owns.

| Without remote state (default) | With remote state (S3 + DynamoDB) |
|-------------------------------|----------------------------------|
| State file on local disk | State file in S3 |
| No collaboration | Whole team shares state |
| No locking | DynamoDB lock prevents concurrent applies |
| Lose laptop → lose state → resources orphaned | Survives any single failure |

**Production setup:**

```hcl
terraform {
  backend "s3" {
    bucket         = "company-tf-state"
    key            = "flask-rest-api/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "tf-state-locks"
  }
}
```

### State File Internals

```bash
terraform state list              # all tracked resources
terraform state show aws_vpc.main # one resource's attributes
terraform state mv old new        # rename without destroying
terraform state rm <addr>         # forget about a resource (doesn't delete in cloud)
terraform state pull > state.json # local copy for debug
```

**Never edit state by hand.** Use `terraform state` commands or `terraform import`.

### `terraform plan` vs `terraform apply`

| Command | Effect |
|---------|--------|
| `terraform plan` | Read-only. Shows what would change. Save with `-out=plan.tfplan` |
| `terraform apply` | Executes changes. Re-runs plan unless given a saved plan file |
| `terraform apply plan.tfplan` | Executes the saved plan exactly — production safety |

**Production workflow:**
```bash
terraform plan -out=plan.tfplan
# review the plan output
terraform apply plan.tfplan      # what you reviewed = what gets applied
```

### Drift Detection

If someone manually changes a resource in AWS console:

```bash
terraform plan          # shows diffs (drift)
terraform apply -refresh-only   # update state to match reality, don't change cloud
terraform apply         # OR force cloud back to terraform's expected state
```

### Modules (Production Pattern)

For larger codebases, organize into modules:

```
terraform/
├── main.tf                          # Wires everything together
├── modules/
│   ├── vpc/                         # Reusable VPC module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── eks/
│   └── rds/
└── envs/
    ├── dev/main.tf                  # Dev-specific tfvars
    ├── staging/main.tf
    └── prod/main.tf
```

Use community modules from the [Terraform Registry](https://registry.terraform.io) — `terraform-aws-modules/vpc/aws` is famous and battle-tested.

### Workspaces (Multi-Environment)

```bash
terraform workspace new dev
terraform workspace new prod
terraform workspace select dev
terraform apply -var-file=dev.tfvars
```

Each workspace has its own state file. Use cautiously — for fully isolated envs, prefer separate state files (S3 keys per env).

---

## Part B — Ansible Deep Dive

### File Structure

```
ansible/
├── playbook.yaml          # Orchestration — includes all task files
├── inventory.ini          # Target hosts (with SSH details)
├── group_vars/
│   └── all-variables.yaml # Variables shared across all hosts
└── tasks/
    ├── system_setup.yaml  # OS-level updates, hostname
    ├── basic_tools.yaml   # git, curl, vim
    ├── docker.yaml        # Docker engine + compose
    ├── kubernetes.yaml    # kubectl, kubeadm, kubelet
    ├── terraform.yaml     # Terraform binary
    ├── ansible.yaml       # Ansible itself
    └── cleanup.yaml       # apt cache, temp files
```

### Playbook ([playbook.yaml](../ansible/playbook.yaml))

```yaml
- name: Bootstrap fresh VM with complete DevOps toolset
  hosts: all
  become: yes               # sudo
  gather_facts: yes
  vars_files:
    - group_vars/all-variables.yaml
  tasks:
    - name: Include system setup tasks
      include_tasks: tasks/system_setup.yaml
      tags: system_setup
    - name: Include Docker tasks
      include_tasks: tasks/docker.yaml
      tags: docker
    # ... more includes ...
```

### Inventory ([inventory.ini](../ansible/inventory.ini))

```ini
[new_vms]
dev-vm ansible_host=44.197.15.118 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/api-server.pem

[new_vms:vars]
ansible_python_interpreter=/usr/bin/python3
```

**Group structure:**
- `[new_vms]` — host group
- `[new_vms:vars]` — vars applied to that group

Production: use **dynamic inventory** (queries AWS API for EC2 tags) instead of static IPs.

### Variables ([group_vars/all-variables.yaml](../ansible/group_vars/all-variables.yaml))

```yaml
terraform_version: "1.5.7"
kubectl_version: "v1.28.0"
ansible_version: "8.6.1"
dev_user: "ubuntu"
docker_group: "docker"
timezone: "UTC"
```

Centralize versions in one file → easy upgrades.

### Idempotency

Ansible modules (`apt`, `yum`, `copy`, `template`, etc.) **check current state** before acting. Re-running a playbook on an already-configured host: zero changes.

**Good — idempotent:**
```yaml
- name: Install Docker
  apt:
    name: docker.io
    state: present
```

**Bad — not idempotent:**
```yaml
- name: Install Docker
  shell: apt-get install -y docker.io   # Runs every time, no check
```

Use `command` / `shell` only as last resort. Prefer dedicated modules.

### Tags

Tags allow running subsets of a playbook:

```bash
ansible-playbook -i inventory.ini playbook.yaml --tags docker
ansible-playbook -i inventory.ini playbook.yaml --skip-tags cleanup
```

### Roles (Production Pattern)

For larger plays, structure into reusable **roles**:

```
roles/
├── docker/
│   ├── tasks/main.yml
│   ├── handlers/main.yml      # restart services
│   ├── templates/daemon.json.j2
│   ├── files/
│   ├── vars/main.yml
│   └── defaults/main.yml      # default vars
├── monitoring/
└── kubernetes/
```

Use Ansible Galaxy roles for common things (`geerlingguy.docker`).

### Ansible Vault (Secrets)

```bash
ansible-vault encrypt group_vars/all-variables.yaml
ansible-vault edit group_vars/all-variables.yaml
ansible-playbook ... --ask-vault-pass
```

Encrypts entire YAML files. Decryption key is shared via secure channel (1Password, secret manager).

---

## Commands Reference

### Terraform

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Init working dir | `terraform init` | Downloads providers, sets up backend |
| 2 | Format files | `terraform fmt` | Auto-format `.tf` files |
| 3 | Validate syntax | `terraform validate` | Pre-flight check (no API calls) |
| 4 | Show planned changes | `terraform plan -out=plan.tfplan` | Preview + save plan |
| 5 | Apply | `terraform apply plan.tfplan` | Execute the saved plan |
| 6 | Show outputs | `terraform output` | Print all outputs |
| 7 | Show one output (sensitive ok) | `terraform output -raw alb_dns_name` | For scripts |
| 8 | List state | `terraform state list` | All resources Terraform tracks |
| 9 | Show one resource | `terraform state show aws_vpc.main` | All attributes |
| 10 | Import existing | `terraform import aws_vpc.main vpc-1234` | Add a manually-created resource to state |
| 11 | Refresh state from cloud | `terraform apply -refresh-only` | Update state without changing infra |
| 12 | Targeted apply | `terraform apply -target=aws_vpc.main` | Apply just one resource (debugging only) |
| 13 | Destroy | `terraform destroy` | Tear down everything |
| 14 | Show graph | `terraform graph \| dot -Tpng > g.png` | Visualize dependency graph |
| 15 | Force unlock | `terraform force-unlock <LOCK_ID>` | Recover from crashed apply |

### Ansible

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Test SSH connectivity | `ansible all -i inventory.ini -m ping` | Verify reachability before playbook |
| 2 | Run playbook | `ansible-playbook -i inventory.ini playbook.yaml` | Full run |
| 3 | Run only one tag | `... --tags docker` | Subset |
| 4 | Skip a tag | `... --skip-tags cleanup` | Exclude |
| 5 | Dry run (check mode) | `... --check` | Show what would change |
| 6 | Verbose | `... -v` (or `-vvv` for max) | Debug |
| 7 | Inventory dump | `ansible-inventory -i inventory.ini --list` | Inspect parsed inventory |
| 8 | Encrypt file | `ansible-vault encrypt group_vars/secrets.yaml` | Hide secrets in git |
| 9 | Run with vault | `ansible-playbook ... --ask-vault-pass` | Decrypt at runtime |
| 10 | Ad-hoc command | `ansible all -i inv.ini -a "uptime"` | One-shot, no playbook needed |

---

## Troubleshooting (Real-World Scenarios)

### Terraform — Top Issues for Mid/Senior Roles

| Sl. No | Issue | Cause | Diagnosis | Fix |
|--------|-------|-------|-----------|-----|
| 1 | `Error acquiring the state lock` | Previous `apply` crashed mid-way; lock held in DynamoDB | Check the lock owner ID printed in error | If safe (no apply running): `terraform force-unlock <LOCK_ID>` |
| 2 | `No valid credential sources found` | AWS creds not configured | `aws sts get-caller-identity` fails too | `aws configure`, or set `AWS_ACCESS_KEY_ID`/`SECRET` envs, or use SSO/IAM role |
| 3 | `Provider produced inconsistent final plan` | Provider bug or version mismatch | Check provider version | Pin provider in `required_providers`; `terraform init -upgrade` |
| 4 | `cycle in dependencies` | Two resources reference each other | `terraform graph \| dot -Tpng` | Break the cycle with a `data` source or refactor |
| 5 | `Resource already exists` (cloud has it, state doesn't) | Created manually or by another tfstate | Confirm in AWS console | `terraform import aws_vpc.main vpc-1234`; do NOT `apply` blindly |
| 6 | Drift — manual change in console | Someone bypassed Terraform | `terraform plan` shows diffs | Decide: revert via `apply`, or accept via `apply -refresh-only` and update code |
| 7 | `VPC has dependencies and cannot be deleted` | Subnets/IGW/NAT still attached | `aws ec2 describe-...` to find them | Destroy in reverse order; or `terraform destroy -target` for orphans |
| 8 | State file corrupted | Mid-apply crash + no backup | `terraform state pull` shows malformed JSON | Restore from S3 versioning OR use `terraform refresh` to rebuild |
| 9 | Plan shows unwanted recreate | `count` index shifted, or attribute change forces replacement (`InvalidParameterCombination`) | `terraform plan` shows `-/+` (destroy + create) | Refactor to `for_each`; use `lifecycle { ignore_changes = [...] }` for cosmetic-only changes |
| 10 | Sensitive data in state | RDS password, secrets in resource attrs | `terraform state show` shows them | State files MUST be encrypted at rest (S3 SSE); restrict S3 read perms |
| 11 | `count` evaluates `null` or `unknown` | Dependent on resource not yet created (chicken-and-egg) | Plan errors with "value is unknown" | Use a `data` source instead, or split into stages |
| 12 | Slow plan/apply (5+ min) | Many resources + remote state | `terraform plan -refresh=false` | Disable refresh during dev; use `-target` to scope; consider Terragrunt for parallelization |
| 13 | `Error releasing the state lock` | Lock owner mismatch | Lock holds till explicit release | `terraform force-unlock` after confirming no concurrent apply |
| 14 | Different team members get different plans | Local state files diverge | No remote backend | **Migrate to S3 + DynamoDB backend immediately** |
| 15 | Costs explode after `apply` | NAT GW, ALB, EBS volumes all running | AWS Cost Explorer | Always run `terraform destroy` after testing; use AWS Budgets alerts; tag resources for cost attribution |
| 16 | `Module not installed` | New module added to code, no `init` | Plan errors immediately | `terraform init` to download |
| 17 | `Backend initialization required` | Backend config changed | Plan refuses to start | `terraform init -reconfigure` (or `-migrate-state` to copy old state) |
| 18 | `Plugin reinitialization required` | Provider version updated | Plan refuses | `terraform init -upgrade` |
| 19 | `for_each` map has unknown values | Map keys depend on resource being created | Plan errors | Use known-at-plan-time values for keys (e.g., var inputs, not resource attributes) |
| 20 | `terraform destroy` won't remove a resource | `lifecycle { prevent_destroy = true }` set | Error message names the lifecycle | Edit code to remove the protection, then destroy |
| 21 | RDS replacement deletes your DB! | Changing certain attributes forces replacement | Plan shows `-/+` | Use `lifecycle { create_before_destroy = true }`, or take snapshot first |
| 22 | EIP cost surprise | EIP not attached after instance termination | AWS charges for unattached EIPs | Always reference EIPs from running resources; clean up in destroy order |
| 23 | Provider rate-limit errors | Many resources, hitting AWS API limits | `Error: Rate exceeded` | Set `parallelism=10` (default) lower: `terraform apply -parallelism=5` |
| 24 | Workspace state confusion | Wrong workspace selected | `terraform workspace show` | Always check workspace before applying; consider per-env directories instead of workspaces |

### Production Issues You'll Be Asked About in Interviews

#### Issue: "Someone deleted a critical IAM role manually"

**Diagnosis:**
- `terraform plan` will want to **recreate** it
- But: in-flight requests using the role are now broken; recreation may not restore policies attached out-of-band

**Fix:**
- `terraform apply -refresh-only` first to see drift
- If recreation is safe (no out-of-band attachments): `terraform apply`
- If unsafe: `terraform import` the recreated resource (after manual recreation matching original config)
- Long-term: enable AWS Config rules to alert on out-of-band IAM changes; restrict console permissions

#### Issue: "We need to migrate from CloudFormation to Terraform without recreating resources"

**Approach:**
1. Write Terraform code that **matches** existing CloudFormation-managed resources
2. `terraform import` each resource by ID (`aws_vpc.main vpc-xxx`, `aws_subnet.public[\"us-east-1a\"] subnet-yyy`)
3. `terraform plan` until no diffs (iterative — usually requires tweaking the code)
4. Delete the CloudFormation stack with `--retain-resources` flag

#### Issue: "terraform.tfstate accidentally committed to git"

**Severity:** Critical — state files contain secrets in plaintext (RDS passwords, etc.)

**Fix:**
1. **Rotate every secret** in the state file (DB passwords, IAM access keys)
2. Remove from git history: `git filter-repo --path terraform.tfstate --invert-paths`
3. Force-push and notify all collaborators to re-clone
4. Configure remote backend (S3 + DynamoDB) immediately
5. Add `*.tfstate` and `.terraform/` to `.gitignore`

#### Issue: "Two engineers ran `terraform apply` simultaneously"

**Diagnosis:**
- Without remote state lock: state file is now corrupted
- With S3 + DynamoDB lock: second apply fails with lock error (correct behavior)

**Fix (corrupted state):**
1. Restore from S3 versioning (`aws s3api list-object-versions`)
2. Run `terraform plan` to verify
3. If can't restore: `terraform refresh` to rebuild from cloud (data loss for resource metadata not in cloud)

### Ansible — Top Issues

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | `Permission denied (publickey)` | Wrong key or path | Verify `ansible_ssh_private_key_file`; `chmod 600 key.pem`; test with `ssh -i key.pem user@host` |
| 2 | `Failed to connect to the host via ssh` | Host unreachable, security group blocks | Confirm SG allows your IP on port 22; `ping`; `telnet host 22` |
| 3 | `sudo: a password is required` | `become: yes` but no NOPASSWD sudo | Add user to sudoers with NOPASSWD, or `--ask-become-pass` |
| 4 | Module imports fail on target | Wrong Python interpreter | Set `ansible_python_interpreter=/usr/bin/python3` in inventory |
| 5 | Playbook hangs at `gather_facts` | Reverse DNS slow | Set `gather_facts: false` for speed; gather selectively |
| 6 | `apt: Could not get lock /var/lib/dpkg/lock` | Another apt process | Wait/retry; or add `until: result is succeeded retries: 5 delay: 10` |
| 7 | Vault file edit doesn't take effect | Wrong vault password | Verify with `ansible-vault view`; rotate if forgotten |
| 8 | Variables not interpolating | Wrong precedence (extra-vars > playbook > group_vars > defaults) | Run with `-vvv` to see resolved values |
| 9 | Idempotent playbook re-installs every run | Using `shell` / `command` instead of dedicated module | Switch to `apt`, `yum`, `copy`, `template` modules |
| 10 | "Host is not in inventory" | Inventory file path wrong | Check `-i path/to/inventory.ini`; use absolute path |

---

## Interview Q&A

### Terraform

| Q | A |
|---|---|
| **What is Terraform's state file and why is it important?** | A JSON file mapping Terraform code to real-world resources. Without it, Terraform has no idea what it owns. Production must use a remote backend (S3 + DynamoDB) for collaboration and locking. |
| **`count` vs `for_each`?** | `count` for true lists (indexed). `for_each` for maps/sets (keyed by string). `for_each` is preferred — removing items doesn't shift indexes and recreate everything. |
| **What happens during `terraform apply`?** | Refreshes state from cloud → builds dependency graph from code → computes diff → executes changes in DAG order, in parallel where possible (default: 10 concurrent ops). |
| **How do you handle secrets in Terraform?** | Don't put them in `.tf` files. Use SSM/Vault and read via `data` blocks. State file STILL contains them — encrypt state at rest (S3 SSE). For input secrets, use `TF_VAR_xxx` env vars or `terraform.tfvars` (gitignored). |
| **What's drift detection?** | `terraform plan` compares state to actual cloud state, shows differences. If someone manually changed a resource in console, plan reveals the drift. |
| **What's `terraform import`?** | Adopts an existing cloud resource into Terraform state. Doesn't generate code — you write the config first, then import. Painful at scale; `terraformer` can help. |
| **Difference between `apply -refresh-only` and `apply`?** | `-refresh-only` updates state to match cloud reality (accepts drift). `apply` forces cloud back to state (rejects drift). |
| **Modules — what & why?** | Reusable Terraform code. Improves DRY, testability, version pinning. Community modules (terraform-aws-modules) are battle-tested. |
| **Workspaces — when to use?** | Multiple environments with the same code. **Caveats:** all workspaces share the same backend; not great for fully isolated envs (use separate state files instead). |
| **What's a provider?** | A plugin that translates Terraform code to API calls (AWS, Azure, K8s, GitHub, etc.). Multiple providers can coexist. |
| **How does Terraform handle dependencies?** | Implicit (via attribute references) → builds DAG. Explicit `depends_on` for non-code dependencies. |
| **What's `lifecycle`?** | Per-resource block: `create_before_destroy` (rolling replace), `prevent_destroy` (safety lock), `ignore_changes` (allow specific drift). |
| **How do you handle partial failure during `apply`?** | Terraform marks failed resources as tainted. Re-running `apply` will retry. State may need cleanup with `terraform state rm` if a resource was partially created in cloud but not tracked. |
| **What's `terraform taint` (deprecated) / `apply -replace`?** | Forces a resource to be destroyed and recreated on next apply. Useful when state is fine but the actual resource needs replacement. |
| **What's a backend?** | Where state is stored. `local` (default), `s3`, `gcs`, `azurerm`, `consul`, `terraform cloud`, etc. Production = remote backend with locking. |
| **What's Terragrunt?** | Wrapper around Terraform for DRY multi-env setups. Provides remote state config, common variables, dependency management between modules. |
| **How do you organize Terraform for a company with 100 microservices?** | Per-service repos OR mono-repo with module per service. Shared modules (VPC, EKS) in a separate repo. Use Terragrunt for DRY env config. State files per env per service. |
| **What's `data` source?** | Read-only reference to existing infrastructure (e.g., `data "aws_vpc" "default" { default = true }`). Doesn't manage the resource — just queries. |
| **Provider vs Module vs Resource?** | **Provider** — plugin to a target API (aws, kubernetes). **Resource** — one thing to create (`aws_vpc`). **Module** — reusable group of resources. |
| **How do you do canary infra changes?** | Deploy to a separate workspace/account first; verify; then promote to prod. Or use `-target` to apply small changes incrementally. |
| **What's policy-as-code in Terraform?** | Tools like OPA, Sentinel, or `terraform-compliance` validate plans against policies (e.g., "no public S3 buckets"). Run in CI to block bad applies. |

### Ansible

| Q | A |
|---|---|
| **Idempotency — why does it matter?** | A playbook should produce the same end state regardless of how many times it's run. Lets you re-run safely after partial failures. Achieved by using state-aware modules (apt, copy) instead of raw shell. |
| **Push vs Pull?** | Ansible is **push** (control machine → targets via SSH). Puppet/Chef are **pull** (agent on target queries server). Push = simpler, no agent; pull = scales better for huge fleets. |
| **What's a handler?** | A task that runs only when **notified** by another task. Common pattern: a config file change "notifies" a handler that restarts the service. |
| **What's the difference between `vars`, `group_vars`, `host_vars`?** | All variables, different scope. Precedence (low to high): defaults → inventory vars → group_vars → host_vars → playbook vars → extra-vars (`-e`). |
| **How to deal with secrets in Ansible?** | `ansible-vault` to encrypt files. For dynamic secrets, use lookup plugins (`hashicorp_vault`, `aws_secret`). |
| **What's a role?** | Reusable playbook structure (tasks/handlers/templates/vars/defaults/meta). Industry standard for organizing larger Ansible code. |
| **What's the `template` module?** | Renders a Jinja2 template file (with variables) and copies to target. Used for config files like nginx.conf, prometheus.yml. |
| **What's dynamic inventory?** | Inventory generated at runtime by querying APIs (AWS EC2, K8s, Consul). Replaces static `inventory.ini`. |
| **Difference between `import_tasks` and `include_tasks`?** | `import_tasks` is **static** (parsed at playbook load). `include_tasks` is **dynamic** (parsed at runtime, supports loops/conditionals). |
| **What's `delegate_to`?** | Run a task on a different host than the current target. Useful for "run this on the load balancer" mid-playbook. |
| **How to test Ansible code?** | `--check` mode (dry run); `molecule` (test framework with Docker); `ansible-lint` for static analysis. |

---

## STAR Stories

### Story 1: "Tell me about a time you debugged a Terraform state issue."

**Situation:** A teammate ran `terraform apply` from their laptop while another apply was in progress on the CI runner. The state file in S3 was overwritten partially, and `terraform plan` started showing a 200-line diff that didn't match reality.

**Task:** Recover state without recreating any resources (RDS, EBS volumes had production data).

**Action:**
1. Identified S3 versioning was enabled on the state bucket — pulled the previous version: `aws s3api list-object-versions --bucket tf-state --key prod/terraform.tfstate`
2. Restored: `aws s3api copy-object --copy-source ...?versionId=<id>`
3. Ran `terraform plan` — clean (no diffs)
4. Configured DynamoDB lock table (which we'd been meaning to do): added `dynamodb_table` to backend block + `terraform init -reconfigure`
5. Validated lock by attempting concurrent apply — second one correctly blocked

**Result:** Zero data loss. Established a hard rule in the team: **all applies via CI**, no laptop applies to prod.

**Takeaway:** S3 versioning is the cheap insurance you don't appreciate until you need it. DynamoDB locking is non-optional for any team > 1 person.

---

### Story 2: "Tell me about a time Terraform wanted to delete production data."

**Situation:** Renamed an `aws_db_instance` from `db_main` to `db_primary` for clarity. `terraform plan` showed: `aws_db_instance.db_main` will be **destroyed**, `aws_db_instance.db_primary` will be **created** — destroying our prod RDS!

**Task:** Rename the resource without losing the database.

**Action:**
1. Aborted the apply immediately.
2. Used `terraform state mv aws_db_instance.db_main aws_db_instance.db_primary` to rename in state.
3. Re-ran `terraform plan` — showed no changes (state matches code now).
4. Documented the pattern for the team: "`terraform state mv` for renames, never just rename in code."

**Result:** Avoided a major outage. Added a CI check to refuse plans that destroy stateful resources without manual approval.

**Takeaway:** Terraform identifies resources by their **address in code**, not by their cloud ID. A rename in code = destroy + recreate. `terraform state mv` is the safe rename.

---

### Story 3: "Tell me about a time you reduced cloud spend with IaC."

**Situation:** Monthly AWS bill jumped 30% over a quarter. Investigation showed many forgotten resources from dev experiments — unattached EIPs ($3.60/mo each), ALBs left running, NAT gateways for dead VPCs.

**Task:** Identify and clean up orphaned resources, prevent recurrence.

**Action:**
1. Audited each region's resources via Cost Explorer + AWS Resource Groups.
2. Identified 47 unattached EIPs, 3 idle ALBs, 2 NAT gateways from a deprecated experiment.
3. For Terraform-managed: ran `terraform destroy` on archived workspaces.
4. For non-managed: documented and deleted manually after verifying with owners.
5. Added AWS Config rules: alert on EIPs unattached > 1 hour.
6. CI check: every TF module must include resource tagging (`environment`, `owner`, `cost_center`).
7. Set up daily Cost Anomaly Detection alerts → Slack.

**Result:** $4K/month savings. Anomaly detection caught a forgotten dev cluster within 3 days the next quarter (would have been a $1.5K monthly bill).

**Takeaway:** IaC alone doesn't prevent cost waste — you need tagging discipline + automated alerts. Tag everything from day one.

---

## Production Hardening

### Terraform

| Area | Current Project | Production |
|------|----------------|-----------|
| **Backend** | Local state | S3 backend with DynamoDB locking, versioning enabled, encryption-at-rest |
| **Modules** | Single `main.tf` | Per-component modules (vpc, eks, rds), versioned via git tags |
| **Multi-env** | Single state | Separate state files per env (dev/staging/prod), or Terraform workspaces |
| **Secrets** | Plain in `.tfvars` | SSM/Vault data sources; `TF_VAR_xxx` env vars; sensitive outputs |
| **Cloud auth** | Static IAM keys | OIDC from CI to AWS (no static creds) |
| **CI integration** | Manual `apply` | Atlantis or Terraform Cloud for PR-based plan/apply |
| **Drift detection** | Manual `plan` | Scheduled `plan` in CI; alert on diffs |
| **Policy** | None | OPA/Sentinel/Checkov for policy-as-code; Terraform-compliance for BDD-style tests |
| **Testing** | None | Terratest (Go-based) for module tests; `terraform validate` in CI |
| **Documentation** | Inline comments | `terraform-docs` to auto-generate README per module |
| **Cost estimation** | None | `infracost` in CI to show $ delta of plans in PR comments |
| **Tagging** | Some | Mandatory tags via Sentinel policy; AWS Config rule to enforce |
| **Lifecycle protection** | None | `lifecycle { prevent_destroy = true }` on RDS, S3 buckets, IAM roles |
| **Resource granularity** | Per-resource files | Group related resources; use clear naming conventions |

### Ansible

| Area | Current | Production |
|------|---------|-----------|
| **Inventory** | Static `inventory.ini` | Dynamic inventory plugin (`amazon.aws.aws_ec2`) |
| **Secrets** | Plain in vars files | `ansible-vault` or external lookup (Vault, AWS Secrets Manager) |
| **Roles** | Inline tasks | Role-based structure with handlers, templates, defaults |
| **Testing** | None | `molecule` with Docker driver; `ansible-lint` in CI |
| **Idempotency** | Some `shell` calls | Replace with proper modules; add `--check` to CI |
| **Logging** | stdout | Use `ansible-runner` with structured logging; log to ELK/Loki |
| **Tower / AWX** | None | Self-service playbook execution UI; RBAC, audit log |
| **Bootstrap** | Manual SSH access | Cloud-init for first boot; Ansible takes over after |

---

## Cloud Mapping

### Terraform Equivalents in Cloud-Native Tools

| Terraform | AWS-Native | GCP | Azure |
|-----------|-----------|-----|-------|
| Terraform | CloudFormation, CDK, SAM | Deployment Manager, GCP CDK | ARM Templates, Bicep |
| State backend (S3) | CloudFormation stack metadata | Deployment Manager state | Resource Manager state |
| `terraform plan` | CloudFormation changesets | Deployment Manager preview | What-If deployment |
| Modules | CloudFormation nested stacks | Deployment Manager templates | Linked templates |
| Variables | CloudFormation parameters | DM template properties | ARM parameters |
| Outputs | CloudFormation outputs | DM outputs | ARM outputs |
| `import` | `aws cloudformation register-type` | DM import | Resource import |

**Why most teams pick Terraform over CloudFormation:** Multi-cloud, larger ecosystem, better state management, cleaner syntax (HCL vs YAML/JSON), faster iteration.

### Ansible Equivalents

| Ansible | AWS | GCP | Azure |
|---------|-----|-----|-------|
| Ansible | Systems Manager (SSM) | OS Config | Automation State Configuration (DSC) |
| Roles | SSM documents | OS Config policies | DSC configurations |
| Vault | Secrets Manager | Secret Manager | Key Vault |
| Dynamic inventory | SSM Inventory | Asset Inventory | Resource Graph |

---

## What We'd Run on Cloud (If We Deployed)

```bash
# 1. Configure AWS credentials
aws configure

# 2. Create EC2 key pair
aws ec2 create-key-pair --key-name dev-key --query 'KeyMaterial' --output text > dev-key.pem
chmod 600 dev-key.pem

# 3. Find your IP for SSH allow-list
MY_IP=$(curl -s https://checkip.amazonaws.com)

# 4. Provision infrastructure
cd terraform
terraform init
terraform plan \
  -var "key_name=dev-key" \
  -var "my_ip=${MY_IP}/32" \
  -out=plan.tfplan
terraform apply plan.tfplan

# 5. Get bastion IPs
terraform output bastion_public_ips

# 6. Bootstrap with Ansible
cd ../ansible
# Update inventory.ini with the bastion IPs from terraform output
ansible all -i inventory.ini -m ping
ansible-playbook -i inventory.ini playbook.yaml

# 7. (Eventually) tear down
cd ../terraform
terraform destroy
```

**Estimated cost if left running:** ~$100/month for this architecture (2 NAT gateways = $64, ALB = $20, 2 EC2 t3.micro = $8 in free tier or $15 paid, EIPs $14). Always destroy after experimenting.

---

## Reference Links (Internal)

- Terraform main: [terraform/main.tf](../terraform/main.tf)
- Terraform variables: [terraform/variables.tf](../terraform/variables.tf)
- Terraform outputs: [terraform/outputs.tf](../terraform/outputs.tf)
- Ansible playbook: [ansible/playbook.yaml](../ansible/playbook.yaml)
- Ansible inventory: [ansible/inventory.ini](../ansible/inventory.ini)
- Ansible variables: [ansible/group_vars/all-variables.yaml](../ansible/group_vars/all-variables.yaml)
- Ansible tasks: [ansible/tasks/](../ansible/tasks/)
