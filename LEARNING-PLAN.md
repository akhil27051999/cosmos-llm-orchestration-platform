# LEARNING-PLAN.md — Cosmos, the depth-first week-by-week schedule

> **What this is.** The calendar. `MASTER-BUILD-PROGRAM.md` says *what* to build (12 stages);
> `DEVOPS-CALIBRATION.md` says *how hard each piece is for me* and where to go deep; **this doc turns
> that into weeks.** It supersedes every earlier "8-week plan" reference in the other docs.
>
> **Calibrated for:** a senior DevOps/SRE engineer (~5 yrs) targeting **Cloud Solution Architect**,
> learning **depth-first** at **~8–10 hrs/week**. Total: **~56 weeks (~13 months)**, deliberately unrushed.
>
> **Project title:** **Cosmos — Cloud-Native LLM Orchestration Platform.**

---

## The method — every stage runs the same 4-beat loop

1. **Read before you build** — hit the concepts + readings first; you must explain *why* the thing exists before touching the keyboard.
2. **Design in prose** — model/API/state-machine in plain English or a diagram; get it pressure-tested. No code yet.
3. **You write 100% of the code** — Claude never writes the implementation (repo hard rule). Unblock with concepts, not snippets.
4. **Review + interrogate + ADR** — hunt race conditions and weak tradeoffs, defend every "why," then write a 1-page ADR. Target: **30+ ADRs** by the end.

**Golden rule:** one stage at a time; it must *run* before moving on.

---

## Effort weighting (from DEVOPS-CALIBRATION.md)

- 🔴 **Deep-new** (~60% of hours): Stages **0.5, 0, 1, 3, 4, 5** — application Python, distributed-systems *implementation*, the agent layer, data-at-scale.
- 🟡 **Extend** (~30%): Stages **2, 6, 9**, the Go/gRPC half of **7**, multi-region of **11**.
- 🟢 **Leverage** (~10%): Stages **8, 10, 12**, the mesh of **7**, Terraform mechanics of **11** — already operated daily; compress + showcase.

**⭐ Go-to-90% anchors:** Stage 4 (resilience), Stage 8 (custom Operator), Stage 12 (SLO/observability-as-architecture). Stage 3 (agents) is non-negotiable too.

---

## The calendar at a glance

| Phase | Weeks | Stages | Tier | Focus |
|---|---|---|---|---|
| A — Language & app discipline | 1–7 | 0.5, 0 | 🔴 | The #1 gap: *application* Python ≠ scripting Python |
| B — The distributed core | 8–14 | 1, 2 | 🔴/🟡 | Queues, state machines, event sourcing *in code* |
| C — The agent layer ⭐ | 15–19 | 3 | 🔴 | Emergent core; fully new |
| D — Resilience ⭐ #1 | 20–24 | 4 | 🔴 | SRE intuition → LLD you can defend |
| E — Event-driven backbone | 25–29 | 5 | 🔴 | Kafka/CQRS/Saga/CDC in code |
| F — Multi-tenancy & identity | 30–32 | 6 | 🟡 | OAuth2/OIDC app logic + isolation |
| G — Internal comms & Go | 33–36 | 7 | mixed | Go + gRPC new; mesh is leverage |
| H — K8s deep + Operator ⭐ #2 | 37–40 | 8 | 🟢 | Spend weeks on the custom Operator + CRD |
| I — Frontend + A/B framework | 41–44 | 9 | 🔴/🟡 | React/Next/TS + experimentation |
| J — Preview environments | 45–47 | 10 | 🟡 | Reuses the Stage-8 operator + GitOps |
| K — Cloud, IaC, multi-region | 48–52 | 11 | mixed | Terraform mechanics yours; multi-region reasoning new |
| L — Observability/SRE/chaos/capstone ⭐ #3 | 53–56 | 12 | 🟢 | "I instrumented this system and set its SLOs" |

**~60% of hours land in weeks 1–29 (the spine). Own Stages 0.5→5 cold; the back half rides existing infra muscle.**

---

## Phase A — Language & app discipline (Weeks 1–7) 🔴

### Stage 0.5 — Python + testing foundations (Wks 1–4)
*(Moved ahead of the FastAPI rewrite: you can't reason about later async races if the language is shaky.)*
- **Build:** a small typed, tested async service module with a real DB migration — no distributed systems yet.
- **Own:** `typing` + Pydantic v2; generators/coroutines vs `async/await`; context managers; decorators; **pytest** (fixtures, parametrize, mocking) + `hypothesis`; **async SQLAlchemy + Alembic**; `uv`/packaging.
- **Read:** *Fluent Python* (data-model + async chapters); FastAPI+SQLAlchemy async tutorial; pytest docs.
- **Done when:** you can write a typed async module with a migration and a meaningful test suite, and explain event-loop mechanics aloud.

### Stage 0 — FastAPI rewrite + clean architecture (Wks 5–7)
- **Build:** rewrite CRUD to **FastAPI**; hexagonal (ports/adapters); validation; consistent errors; correlation IDs; **idempotency keys**; **optimistic concurrency (OCC)**; 12-factor config.
- **Own:** why hexagonal isolates domain from I/O; idempotency vs at-least-once; OCC vs pessimistic locking.
- **Read:** *Fundamentals of Software Architecture*; 12factor.net; Cloud Design Patterns (*Idempotency*, *Health Endpoint Monitoring*).

---

## Phase B — The distributed core (Weeks 8–14)

### Stage 1 — Async core: queue, state machine, event sourcing (Wks 8–11) 🔴
- **Build:** submit → **202 + id**; durable queue (Redis Streams to start); worker; explicit job **state machine**; append-only **event log**; at-least-once + **idempotent consumer**; cancellation.
- **Own:** separating "accept" from "process"; event sourcing → state reconstruction; the exactly-once *myth*.
- **Read:** DDIA Ch.1, 5, 9; Cloud Design Patterns (*Queue-Based Load Leveling*, *Competing Consumers*, *Event Sourcing*, *CQRS*).

### Stage 2 — Polyglot persistence: Mongo + Redis (Wks 12–14) 🟡
- **Build:** relational core stays in Postgres; trajectories/payloads → **MongoDB**; Redis hot state. Write the **"why polyglot" ADR**.
- **Own:** embed-vs-reference modeling; aggregation pipeline; change streams; TTL indexes.
- **Read:** DDIA Ch.2; MongoDB *Data Modeling* + "6 Rules of Thumb"; MongoDB University M001/M320.

---

## Phase C — The agent layer ⭐ (Weeks 15–19) 🔴 — the Emergent core

### Stage 3 — Agent loop + RAG
- **Build:** a job type running a real **agent loop with Claude** — plan → tool-call → observe → iterate, bounded by a **token budget**; persist the full **trajectory**; **stream via SSE**; multi-agent patterns (orchestrator-worker, evaluator-optimizer); **RAG** (embeddings + pgvector/Qdrant); a small **eval harness**.
- **Own:** safe loop termination; tool/function calling; context-window & token budgeting; when RAG helps vs hurts.
- **Read:** Anthropic API docs (Messages, tool use) + "Building Effective Agents." *(Invoke the `claude-api` skill for exact API details at build time.)*
- **Note:** small Anthropic spend; Stage-4 resilience wraps these real calls.

---

## Phase D — Resilience ⭐ anchor #1 (Weeks 20–24) 🔴 impl — *go to 90%*

### Stage 4 — Rate-limit / breaker / retry / fallback
- **Build:** runtime **provider registry**; **selector** (round-robin/weighted/least-loaded); **rate limiter** (token bucket + sliding window, distributed via Redis/Lua); **circuit breaker** (closed/open/half-open); **retry + backoff + jitter**; **fallback chain**; **load shedding** — all wrapping the Stage-3 providers.
- **Own:** why jitter matters; half-open probing; when fallback is an anti-pattern; load-shedding vs backpressure.
- **Read:** *Release It!* (stability patterns); **Amazon Builders' Library** (*Timeouts/retries/backoff with jitter*, *Load shedding*, *Avoiding fallback*).
- **Interview story:** "I've *operated* these in Envoy — here's how I *built* them."

---

## Phase E — Event-driven backbone (Weeks 25–29) 🔴

### Stage 5 — Kafka + CQRS + Saga + CDC
- **Build:** **Kafka (Redpanda locally)** backbone; partitions/consumer-groups/replay/exactly-once; DLQ; **schema registry** + evolution; **outbox pattern**; **CQRS** read models; **Saga** for multi-step jobs; **CDC (Debezium)** Postgres→warehouse.
- **Read:** DDIA Ch.11; Confluent "Kafka 101"; microservices.io (*Saga*, *Transactional Outbox*); Debezium docs.

> **End of the spine (Week 29).** Own everything to here and you're already a different candidate.

---

## Phase F–L — the back half (rides existing skills)

### F · Stage 6 — Multi-tenancy & identity (Wks 30–32) 🟡
Tenants, API keys, quotas, usage ledger, **OAuth2/OIDC/JWT** (Keycloak), **Vault** dynamic creds/PKI, prompt-injection defense. *New = app-side auth logic, not Vault ops you know.*

### G · Stage 7 — gRPC, mesh, Go (Wks 33–36) mixed
**gRPC + Protobuf**; **rewrite the worker in Go** (goroutines/channels/`context`); Istio for mTLS + traffic-shaping. *Go + gRPC are the real learning; the mesh is yours.*

### H · Stage 8 — K8s deep + custom Operator ⭐ anchor #2 (Wks 37–40) 🟢
RBAC/NetPol/PSS already yours — **spend the weeks on a custom Operator + CRD** (Kubebuilder) + KEDA + Kyverno/OPA. *"I wrote a Kubernetes operator in Go" is a top-tier differentiator you can reach fast.*

### I · Stage 9 — Frontend + A/B framework (Wks 41–44) 🔴/🟡
Next.js/React/TS dashboard; live trajectory (SSE); **experimentation framework** (feature flags, traffic splitting, significance, guardrails/auto-rollback).

### J · Stage 10 — Preview environments (Wks 45–47) 🟡
Ephemeral per-tenant stacks (vcluster); external-dns + cert-manager; ArgoCD ApplicationSets — *powered by the Stage-8 operator.*

### K · Stage 11 — Cloud, IaC, multi-region (Wks 48–52) mixed
Terraform a real AWS env (VPC/EKS+IRSA/RDS/ElastiCache/MSK/S3/ALB/Route53/CloudFront/ACM/WAF/KMS); then **multi-region reasoning** (active-passive→active-active); FinOps (Infracost). One real deploy to make it concrete.

### L · Stage 12 — Observability/SRE/chaos/capstone ⭐ anchor #3 (Wks 53–56) 🟢
Instrument **your own code** (OTel across async/Kafka/gRPC); **SLOs + burn-rate alerts**; profiling; chaos (Chaos Mesh); supply-chain (SBOM/cosign/SLSA); k6 load test; then capstone artifacts (Well-Architected review, cost model, C4 + Exceptional-4 diagrams, failure playbook, scale-at-100x).

---

## Certifications, woven in
- **CKA early** (background, Wks ~8–14): nearly free for you — quick confidence win. Consider **CKAD** too.
- **AWS SAP-C02** (aim during Phase K): the *Professional* matches Stage 11's depth for a 6–7-YoE architect role. SAA-C03 only as a stepping stone if breadth is rusty.

---

## Progress tracker (update as you go)
- ⬜ Stage 0.5 — Python + testing foundations (Wks 1–4)
- ⬜ Stage 0 — FastAPI rewrite + clean architecture (Wks 5–7)
- ⬜ Stage 1 — Async core (Wks 8–11)
- ⬜ Stage 2 — Polyglot persistence (Wks 12–14)
- ⬜ Stage 3 — Agent loop + RAG (Wks 15–19)
- ⬜ Stage 4 — Resilience (Wks 20–24)
- ⬜ Stage 5 — Event-driven backbone (Wks 25–29)
- ⬜ Stage 6 — Multi-tenancy & identity (Wks 30–32)
- ⬜ Stage 7 — gRPC, mesh, Go (Wks 33–36)
- ⬜ Stage 8 — K8s deep + Operator (Wks 37–40)
- ⬜ Stage 9 — Frontend + A/B framework (Wks 41–44)
- ⬜ Stage 10 — Preview environments (Wks 45–47)
- ⬜ Stage 11 — Cloud, IaC, multi-region (Wks 48–52)
- ⬜ Stage 12 — Observability/SRE/chaos/capstone (Wks 53–56)
