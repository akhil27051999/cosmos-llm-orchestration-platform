# The 12-Stage Build

The spine of the program. Each stage = **a working increment + a concept cluster + a reading list**. Sequence matters — *don't start a stage until the previous one's increment runs.*

**Tier legend (calibrated to the author's background):** 🔴 **NEW** — genuinely new, budget real time · 🟡 **EXTEND** — adjacent to existing skills · 🟢 **LEVERAGE** — already operates it; the work is to author/architect/showcase. ⭐ = a "go-to-90%" anchor.

| Stage | Focus | Tier | What you build |
|---|---|:--:|---|
| **0.5** | Python & testing foundations | 🔴 | Typing, `pytest`, SQLAlchemy/Alembic, packaging & venvs — *application* Python, not scripting. |
| **0** | Foundations & clean architecture | 🔴 | Rewrite to **FastAPI**; hexagonal (ports/adapters); validation, consistent errors, correlation IDs, **idempotency**, **optimistic concurrency**, 12-factor config. |
| **1** | Async core | 🔴 | `202`-accept job submission; durable queue (Redis Streams); worker; explicit **state machine**; append-only **event log**; at-least-once + **idempotent consumer**; cancellation. |
| **2** | Polyglot persistence | 🟡 | Relational core in Postgres; trajectories/payloads → **MongoDB**; Redis hot state. Modeling (embed vs reference), aggregation, **change streams**, TTL. Write the "why polyglot" ADR. |
| **3** ⭐ | The agent layer (LLM + RAG) | 🔴 | Real **agent loop** with Claude — plan→tool-call→observe→iterate, bounded by a **token budget**; persist the **trajectory**; **stream via SSE**; multi-agent patterns; **RAG** (embeddings + vector DB); a small **eval harness**. *The Emergent core.* |
| **4** ⭐ | Routing, registry & resilience | 🔴 | Runtime **provider registry**; **selector** (round-robin/weighted/least-loaded); **rate limiter** (token bucket + sliding window via Redis/Lua); **circuit breaker**; **retry + backoff + jitter**; **fallback chain**; **load shedding** — wrapping the real providers. |
| **5** | Event-driven backbone | 🔴 | **Kafka/Redpanda** (partitions, consumer groups, replay, exactly-once, DLQ); **schema registry** + evolution; **outbox**; **CQRS** read models; **Saga** for multi-step jobs; **CDC (Debezium)** Postgres→warehouse. |
| **6** | Multi-tenancy, identity & security | 🟡 | Tenants, **API keys**, quotas, **usage ledger**, fair scheduling; real IdP (Keycloak/Cognito) with **OAuth2/OIDC/JWT**; **Vault** (dynamic creds, PKI); RBAC; encryption; prompt-injection defenses. |
| **7** | Internal comms: gRPC, mesh, Go | mixed | **gRPC + Protobuf** internally; **rewrite the worker/rate-limiter in Go**; deploy a **service mesh (Istio/Linkerd)** for mTLS + traffic shaping. (Go/gRPC 🔴; mesh 🟢.) |
| **8** ⭐ | Kubernetes deep + custom Operator | 🟢 | Prod k8s (RBAC/NetPol/PSS/PDB); **KEDA** autoscaling on Kafka lag; **build a custom Operator + CRD** (`AgentJob`/`CosmosTenant`); admission control (Kyverno/OPA); Kustomize overlays. *"I wrote a k8s operator in Go" is the top differentiator.* |
| **9** | Frontend + experimentation | 🔴/🟡 | **Next.js/React/TypeScript** dashboard (submit jobs, **live trajectory**, health/usage/breaker views); the **A-B / experimentation framework** — flags, traffic splitting, significance, guardrails/auto-rollback. |
| **10** | Per-tenant preview environments | 🟡 | **Ephemeral preview stacks** on demand (namespace-per-tenant or **vcluster**); **domains + TLS** (external-dns + cert-manager); lifecycle/teardown; GitOps-driven. Powered by the Stage-8 Operator. |
| **11** | Cloud, networking, IaC, multi-region | mixed | **Terraform** a real AWS env (VPC, **EKS + IRSA**, RDS, ElastiCache, MSK, S3, ALB, Route53, CloudFront, ACM, WAF, KMS); then **multi-region** (active-passive → active-active) w/ replication + failover; **FinOps** (Infracost, budgets, tagging). (TF 🟢; multi-region reasoning 🔴.) |
| **12** ⭐ | Observability, SRE, chaos, supply-chain, capstone | 🟢 | Full o11y (**OTel + Prometheus + Loki + Grafana + Pyroscope**); **SLOs + burn-rate alerts**; **chaos (Chaos Mesh)**; **supply-chain** (SBOM, **cosign**, **SLSA**); **load testing (k6)**; then capstone artifacts (Well-Architected review, cost model, failure playbook, scale-at-100×). |

## The spine vs the victory lap

**Stages 0.5 → 5 (the spine)** are where the genuine, new learning lives — ~60% of the effort. *Own these cold.* The back half (7, 8, 10, 12, the mesh part of 7, the Terraform of 11) leans on the author's existing DevOps/SRE muscle — those are fast, showcase-oriented, not slow. See **[[Learning Roadmap]]** for the calendar.

## Pacing

- **6-month track** (~20 hrs/wk): ~2 weeks/stage; skip the optional extremes (Rust, Pulumi, eBPF, GKE multi-cloud).
- **12-month track** (~10 hrs/wk): ~4 weeks/stage; include the extremes; go deep on every ADR.

→ Full readings per stage live in [`MASTER-BUILD-PROGRAM.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/MASTER-BUILD-PROGRAM.md). Effort calibration in [`DEVOPS-CALIBRATION.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/DEVOPS-CALIBRATION.md).
