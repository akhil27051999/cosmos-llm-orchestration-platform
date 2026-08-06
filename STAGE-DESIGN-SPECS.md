# Cosmos — Per-Stage Design Specs

> **What this is.** A build-ready design spec for each stage — so when you sit to code, you already know
> *what* to build. Each spec gives the **goal**, the **data model** (fields in prose/tables, not DDL), the
> **interfaces/API** (described, not coded), the **key mechanisms & decisions**, a **Definition of Done**,
> and the **ADRs** to write. **You write the code; this is the blueprint + the review checklist.**
>
> Design-in-prose only (repo rule). Pair each spec with its segment in `ARCHITECTURE-STUDY-GUIDE.md` and
> concepts in `notes.html`.

---

## Stage 0.5 — Python + testing foundations (Weeks 1–4)

**Goal.** A tiny, typed, tested async module with a real migration — to prove the language + tooling, not distributed systems.

**Data model — one entity, `Job` (sandbox):**
| Field | Type | Notes |
|---|---|---|
| id | UUID | primary key |
| status | enum: pending / running / done / failed | use a `Literal`/enum, not a plain string |
| prompt | str | the task text |
| result | str \| None | filled when done |
| created_at / updated_at | datetime (UTC) | timestamps |

**Interfaces (prose).** A `JobRepository` with async methods: `add(job)`, `get(id) -> Job | None`, `set_status(id, status)`. A thin service function `create_job(prompt) -> Job`. No HTTP yet.

**Key mechanisms & decisions.** Async SQLAlchemy session via `async with`; Alembic migration that creates the `jobs` table; Pydantic model for any external input; typed throughout (mypy clean).

**Definition of Done.** Migration runs; you can create/fetch a job through the repo; a pytest suite (incl. one Hypothesis property) passes; you can explain the event loop aloud.

**ADRs.** "Why async SQLAlchemy + asyncpg"; "Repository pattern for data access."

---

## Stage 0 — FastAPI rewrite + clean architecture (Weeks 5–7)

**Goal.** Turn the module into a real HTTP service with clean layering.

**Data model.** Same `Job`, now with an **idempotency key** (client-supplied, unique) and a **version** integer (for OCC).

**API (prose).**
- `POST /jobs` — body `{prompt, idempotency_key}` → **201** with the job; a repeat with the same key returns the same job (no duplicate).
- `GET /jobs/{id}` — returns the job or 404.
- `GET /healthz` — liveness/readiness.
All bodies validated by Pydantic; errors returned in one consistent shape; every response carries a correlation id.

**Layering (hexagonal).** `domain` (pure `Job` logic, no I/O) ← `application` (services/use-cases) ← `adapters` (FastAPI in, SQLAlchemy out). Dependencies point inward; the domain imports nothing framework-specific. Define **ports** (interfaces like `JobRepository`) in the core, **adapters** implement them.

**Key decisions.** Idempotency keys make retries safe; OCC (compare-and-set on `version`) prevents lost updates; 12-factor config via env.

**Definition of Done.** All three endpoints work; a duplicate idempotency key doesn't create two jobs; a concurrent update is rejected/retried, not silently lost; domain layer has zero framework imports.

**ADRs.** "Hexagonal layering"; "Idempotency-key strategy"; "OCC vs pessimistic locking."

---

## Stage 1 — Async core: queue, state machine, event sourcing (Weeks 8–11)

**Goal.** Separate *accept* from *process*; make work durable and its history provable.

**Data model.**
- `Job` (as before) — but current status is *derived from events*.
- `JobEvent` (append-only): `id, job_id, type (JobCreated/JobStarted/JobSucceeded/JobFailed/JobCancelled), payload, occurred_at, sequence`.

**Flow / interfaces.**
- `POST /jobs` now returns **202 + id** immediately and enqueues the job (Redis Streams to start).
- A **worker** consumes the queue, runs the job, and appends events per transition.
- Current state = fold over the event log (event sourcing).
- `POST /jobs/{id}/cancel` appends a `JobCancelled` event; the worker checks for it.

**State machine (allowed transitions).** `pending → running → (done | failed)`; `pending|running → cancelled`. Reject illegal transitions.

**Key decisions.** At-least-once delivery + **idempotent consumer** (processing the same message twice is safe — key by event id/sequence); no "exactly-once" delivery (achieve *effectively-once*).

**Definition of Done.** Submit returns 202 instantly; killing the worker mid-job and restarting doesn't corrupt state or double-process; you can reconstruct any job's full history from events; cancellation works.

**ADRs.** "202 + queue vs synchronous processing"; "Event sourcing for jobs"; "Idempotent consumer design."

---

## Stage 2 — Polyglot persistence: MongoDB + Redis (Weeks 12–14)

**Goal.** Put each kind of data in the store that fits it.

**Data placement.**
- **Postgres** — jobs, tenants, quotas, ledger (source of truth, ACID).
- **MongoDB** — the full agent **trajectory** / large variable-shape payloads (embed the steps as a sub-document; reference the `job_id`).
- **Redis** — hot state + cache (latest status, dedupe keys), with TTL.

**Mechanisms.** Mongo aggregation pipeline for trajectory queries; **change streams** to react to writes; **TTL indexes** to auto-expire transient data; a cache-aside pattern in Redis (read cache → miss → DB → populate).

**Definition of Done.** Trajectories persist to Mongo and are queryable; hot reads hit Redis; the "why polyglot" ADR is written and defensible.

**ADRs.** "Why polyglot persistence (which data → which store & why)"; "Embed vs reference for trajectories."

---

## Stage 3 — Agent loop + RAG (Weeks 15–19) ⭐

**Goal.** A real agent that plans, uses tools, and is grounded + bounded.

**Data model.** Trajectory = ordered steps: each step `{role, content, tool_call?, tool_result?, tokens}`. A `TokenBudget {max_tokens, used}` per job.

**Flow.** Worker sends goal → Claude → if a **tool call** comes back, run the tool, feed result back, loop → else finalize. Stream partial output via **SSE**. Persist every step. Stop when: done, budget exhausted, or max-iterations hit. **RAG:** embed the query → vector search (pgvector/Qdrant) → inject top-k docs into the prompt.

**Interfaces.** `POST /jobs` gains an agent job type; `GET /jobs/{id}/stream` (SSE) streams the trajectory live.

**Key decisions.** Safe termination (budget + max steps + no-progress detection); tool inputs validated; prompt-injection defense on retrieved/tool content; a small **eval harness** (a set of tasks + expected properties) to catch regressions.

**Definition of Done.** An agent completes a multi-step task using ≥1 tool; output streams live; budget stops runaways; trajectory is fully stored; eval harness runs. *(Uses real Claude API — invoke the `claude-api` skill for exact API details at build time.)*

**ADRs.** "Agent loop termination strategy"; "RAG store choice (pgvector vs Qdrant)"; "Token-budget policy."

---

## Stage 4 — Resilience ⭐ (Weeks 20–24) — go to 90%

**Goal.** Wrap every provider call so one bad provider can't sink the platform.

**Components (each a small, testable unit).**
- **Provider registry** — providers + health + weights, updatable at runtime.
- **Selector** — round-robin / weighted / least-loaded strategy.
- **Rate limiter** — token bucket (+ sliding window), distributed via Redis/Lua.
- **Circuit breaker** — states closed/open/half-open, per provider, with thresholds + cooldown + half-open probe.
- **Retry** — bounded retries, exponential backoff **+ jitter**.
- **Fallback chain** — ordered backups; used deliberately.
- **Load shedding** — reject/queue-drop past a concurrency/latency threshold.

**Key decisions.** Compose them as a pipeline wrapping the Stage-3 provider call; make each independently unit-testable (inject a fake clock/provider); jitter prevents synchronized retry storms.

**Definition of Done.** A flaky fake provider triggers the breaker (open → half-open → closed) correctly; retries back off with jitter; rate limiter holds the configured rate across concurrent workers; under overload the system sheds load and stays responsive; every component has focused tests.

**ADRs.** "Token bucket vs sliding window"; "Breaker thresholds & half-open policy"; "When fallback is/ isn't appropriate"; "Load-shedding trigger."

---

## Stage 5 — Event-driven backbone: Kafka + CQRS + Saga + CDC (Weeks 25–29)

**Goal.** Replace the starter queue with a durable, replayable backbone and add the patterns.

**Design.** Topics per event type; partition by `job_id` (ordering per job); consumer groups for the worker fleet. **Outbox**: write the job + an outbox row in one transaction; a relay publishes to Kafka. **DLQ** for poison messages. **CQRS**: a read-model projection (fast queries) built from events. **Saga**: for multi-step jobs, an orchestrator that issues steps and compensations on failure. **CDC (Debezium)** streams Postgres → warehouse.

**Definition of Done.** Jobs flow through Kafka with per-job ordering; replaying a topic rebuilds the read model; the outbox guarantees no lost/dup events; a failing multi-step job compensates correctly; CDC lands data in the warehouse.

**ADRs.** "Partitioning key & ordering"; "Outbox vs dual-write"; "Saga orchestration vs choreography"; "Effectively-once strategy."

---

## Stage 6 — Multi-tenancy & identity (Weeks 30–32)

**Goal.** Serve many tenants safely, authenticated and billed.

**Data model.** `Tenant {id, name, plan}`; `ApiKey {id, tenant_id, hash}`; `Quota {tenant_id, limit, window}`; `UsageLedger {tenant_id, job_id, tokens, cost, at}`. Every job row carries `tenant_id` (row-level scoping).

**Design.** Keycloak issues/validates OAuth2/OIDC/JWT; a gateway dependency extracts tenant + scopes from the token. Quota check before accept. Vault issues dynamic DB creds. Prompt-injection guard on agent inputs.

**Definition of Done.** A caller must present a valid token; tenant A can never read tenant B's jobs; quota is enforced and usage recorded; secrets come from Vault, not config.

**ADRs.** "Tenant isolation strategy (row-scoped vs schema vs DB)"; "Quota/fair-scheduling algorithm."

---

## Stage 7 — gRPC, service mesh, Go (Weeks 33–36)

**Goal.** Split internal comms onto gRPC; rewrite the worker in Go; add a mesh.

**Design.** Define service contracts in Protobuf (job dispatch, status). Gateway↔worker over gRPC. Rewrite the worker in **Go** (goroutines for concurrency, channels for coordination, `context` for cancellation/timeouts). Deploy **Istio** for mTLS + traffic shaping.

**Definition of Done.** Go worker consumes and processes jobs at parity with the Python one; gRPC contract is versioned; mesh enforces mTLS between services; a canary split works via the mesh.

**ADRs.** "Why Go for the worker"; "gRPC internally vs REST"; "Mesh responsibilities vs app code."

---

## Stage 8 — K8s deep + custom Operator + KEDA ⭐ (Weeks 37–40)

**Goal.** Automate platform ops as native Kubernetes objects.

**Design.** A **CRD** (e.g., `Tenant` or `PreviewEnv`) + a controller with a **reconcile loop** (desired vs actual). KEDA scales workers on **Kafka consumer lag**. Kyverno/OPA enforce policy (no privileged pods, required labels). RBAC/NetworkPolicies/PodSecurity locked down.

**Definition of Done.** Creating a `Tenant` CR provisions its resources automatically and self-heals if deleted; workers scale up under Kafka backlog and to zero when idle; policy violations are rejected at admission.

**ADRs.** "CRD schema & reconcile design"; "Scale-on-lag (KEDA) vs CPU."

---

## Stage 9 — Frontend + experimentation (Weeks 41–44)

**Goal.** A dashboard + a safe way to change agent configs by data.

**Design.** Next.js/React/TS dashboard: submit jobs, live trajectory (SSE), health/usage views. Experimentation service: feature flags, %-traffic splitting across agent configs/models, metric collection, significance test, guardrail auto-rollback.

**Definition of Done.** You can run a job from the UI and watch it stream; an experiment routes a % of traffic to a variant, reports significance, and auto-rolls-back on a guardrail breach.

**ADRs.** "Experiment assignment & guardrail policy."

---

## Stage 10 — Per-tenant preview environments (Weeks 45–47)

**Goal.** On-demand isolated stacks, powered by the Stage-8 operator.

**Design.** `PreviewEnv` CR → operator provisions an isolated stack (vcluster / namespace) → external-dns + cert-manager wire a domain + TLS → Argo CD ApplicationSet deploys → auto-teardown on delete/expiry.

**Definition of Done.** One command/CR yields a working, isolated, TLS'd environment with its own URL; it tears down cleanly and leaves nothing behind.

**ADRs.** "Isolation level (vcluster vs namespace)"; "Lifecycle/TTL policy."

---

## Stage 11 — Cloud, IaC, multi-region (Weeks 48–52)

**Goal.** Real AWS as code; evolve to multi-region.

**Design.** Terraform modules: VPC (multi-AZ public/private), EKS + **IRSA**, RDS, ElastiCache, MSK, S3, ALB, Route 53, CloudFront, ACM, WAF, KMS. Remote state + Terratest. Multi-region: **active-passive** first (replicate data, health-based Route 53 failover) → **active-active** later. FinOps: Infracost in CI, budgets, tagging.

**Definition of Done.** `terraform apply` stands up a working environment; a real deploy runs on it; a region-failover runbook is tested (even if simulated); cost is visible per component.

**ADRs.** "Active-passive vs active-active (with RPO/RTO)"; "IRSA over static keys"; "FinOps guardrails."

---

## Stage 12 — Observability, SRE, chaos, capstone ⭐ (Weeks 53–56)

**Goal.** Instrument what you built; run it like an SRE; produce the portfolio.

**Design.** OTel traces across async/Kafka/gRPC; Prometheus metrics (+ recording rules, Alertmanager); Loki logs; Grafana dashboards; Pyroscope profiling. Define **SLOs** (e.g., submit-latency, job success rate) + **error budgets** + **burn-rate alerts**. Chaos Mesh experiments. Supply chain: SBOM + cosign + SLSA in CI. k6 load test.

**Definition of Done.** A single request is traceable end-to-end; dashboards + SLO burn-rate alerts exist; a chaos experiment proves a resilience property; images are signed & verifiable; a load test establishes capacity. **Capstone artifacts:** 30+ ADRs, Well-Architected review, cost model, C4 + failure playbook, scale-at-100x.

**ADRs.** "SLO definitions & error budgets"; "What chaos experiments prove"; "Supply-chain trust model."

---

## How to use these specs
1. Read the matching **study-guide segment** (the *why*) + **notes lesson** (the *how* of the language).
2. Design your version in prose first; bring it to review; then **write the code yourself**.
3. Check against the **Definition of Done**; write the listed **ADRs** as you decide.
4. It must *run* before you start the next stage.
