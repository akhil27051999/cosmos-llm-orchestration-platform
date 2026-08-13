# Current Platform (built today)

Before the Cosmos flagship, this repo is a **production-style DevOps reference architecture**: a Flask + PostgreSQL REST API taken through the full lifecycle from local dev to GitOps-managed Kubernetes with observability. This is the foundation Stage 0 rewrites and the later stages build on.

## The modules (current lifecycle)

| # | Module | What it covers |
|---|---|---|
| **1** | [Local Application Setup](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/app/local-setup.md) | Flask + PostgreSQL API, venv, `.env`, running locally |
| **1B** | [Application Testing](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/app/app-testing.md) | Test suite for the API |
| **2** | [Containerization](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/containerization.md) | Docker (multi-stage) + Docker Compose stack |
| **3** | [CI Pipeline](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/cicd.md) | GitHub Actions build/test/push |
| **4** | [Infrastructure as Code](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/iac.md) | Terraform + Ansible |
| **5** | [Kubernetes Orchestration](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/k8s-orchestration.md) | Manifests, StatefulSets, Vault, deployment |
| **6** | [GitOps with Helm + ArgoCD](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/gitops.md) | App-of-Apps, ArgoCD sync loop |
| **7** | [Observability](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/observability.md) | Prometheus + Grafana + Loki + Alertmanager |

## Quick start

**1. Local app**
```bash
git clone https://github.com/akhil27051999/cosmos-llm-orchestration-platform.git
cd cosmos-llm-orchestration-platform
# configure .env (see Module 1), then run the app
```

**2. Containerized stack (Docker Compose)**
```bash
docker compose up -d
```

**3. Kubernetes stack** — create a cluster, install ArgoCD, then bootstrap via the App-of-Apps root application. Vault unseal + `vault-token` secret steps are in Module 5.

**4. Trigger the GitOps loop** — push to the tracked branch; ArgoCD reconciles within ~3 minutes (or sync immediately).

> Exact commands live in the [README Quick Start](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/README.md#quick-start). The [`Makefile`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/Makefile) and [`bootstrap.sh`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/bootstrap.sh) wrap common tasks.

## How this maps to Cosmos

Most of this stack is **🟢 leverage** for the author (see [[Learning Roadmap]]): the K8s, GitOps, IaC, and observability muscle is already here. The Cosmos program's job is to (a) rewrite the app core to FastAPI + clean architecture (Stage 0), (b) add the genuinely new distributed-systems / agent / resilience layers (Stages 1–6), and (c) turn the existing infra skills into architect-grade showcases (Stages 7–12).

→ Next: **[[Repository Structure]]** · **[[The 12 Stage Build]]**
