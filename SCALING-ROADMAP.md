# Scaling Roadmap: From CRUD to a Distributed Job Orchestration Platform

> **Purpose.** Turn this repo from a 5-endpoint Student CRUD into a system that *forces* you to learn and defend Machine Coding (MC), Low-Level Design (LLD), and High-Level Design (HLD) — the three rounds in Emergent's interview guide. You write the code; this doc is the map, the concepts, and the acceptance criteria.
>
> **Working mode.** Roadmap + curriculum. Each phase tells you *what to build, why it matters, which concepts to learn cold, what "done" looks like, and how to rehearse it as an interview answer.* Code is yours to write — that's where the learning sticks.
>
> **⚠️ Status (updated 2026-06-30):** Superseded as the spine by **`MASTER-BUILD-PROGRAM.md`** (the full 6–12 month, 12-stage program). The 7 phases here map to **Stages 0–6** of that program and their acceptance criteria remain valid for those stages. Stages 7–12 (Mongo, agents/RAG, Kafka, gRPC/mesh/Go, custom Operator, frontend, A/B framework, preview-envs, multi-region cloud, supply-chain/chaos) live only in the master program. **Note:** the snippets below predate the "no code" rule — treat them as illustrative *targets*, not code to copy.

---

## 0. The strategy in one screen

### Where you are
- **App (thin):** 5 endpoints, one `students` table, no concurrency, no async, no state, no failure handling.
- **Platform (deep):** Docker, K8s, Helm, ArgoCD/GitOps, Terraform, Ansible, Vault + External Secrets, Prometheus/Grafana/Loki, CI. This already earns most of the HLD rubric's *operational maturity* and *deployment strategy* signal.

### The imbalance to fix
Your infra is ahead of your application. In a product-company loop that reads as *"deploys systems but can't design them."* The fix is to grow the **application domain** until it demands the patterns the rounds test — then your platform layer becomes the operations story on top.

### The target system — **"Cosmos"**
An async **job orchestration platform** that doubles as an **LLM gateway**. Clients submit *jobs* (an LLM completion, a bulk import, a report — anything that can't finish in one request cycle). The platform:

1. Accepts the job at an **API gateway** → returns `202 + job_id` immediately (async).
2. Picks a **provider/model** from a **registry** under **rate-limit** and **health** constraints.
3. Enqueues work; a **worker fleet** processes it with **retries + fallback**.
4. Drives each job through a **state machine**, persisting every transition (**event sourcing**).
5. Exposes status, results, metrics; supports **idempotency**, **cancellation**, **multi-tenant quotas**.

Why this domain wins:
- **MC:** token-bucket + sliding-window rate limiter, circuit breaker (state machine), retry w/ backoff+jitter, fallback chain, bounded-concurrency worker pool, in-memory time-series.
- **LLD:** schemas for jobs/events/providers/idempotency/quotas, optimistic concurrency (version guards), idempotency keys, event sourcing + CQRS, compaction/archival, expand-contract migrations.
- **HLD:** gateway + queue + worker fleet + registry + Postgres + Redis; sync vs async paths; failure domains; scale math (QPS, p99, queue depth, autoscaling).
- **Reuses your DevOps:** two deployables (gateway, worker), HPA on queue depth, canary via Argo, SLOs on the new golden signals.

---

## 1. Target architecture (the diagram you'll grow into)

You will *redraw this in Excalidraw* for the HLD round — this ASCII version is the reference for "what good looks like." Solid = sync, `┄┄` = async, grouped boxes = planes.

```
                          ┌───────────────────────── CONTROL PLANE ─────────────────────────┐
                          │   Provider Registry API     Admin/Tenant API     Config store    │
                          │   (CRUD providers,           (tenants, keys,      (feature flags) │
                          │    weights, limits)           quotas)                             │
                          └───────────────▲──────────────────────▲───────────────────────────┘
                                          │ reads registry        │ reads tenant/quota
  client ──HTTP──►  ┌───────────────────────────────────┐
  (job submit)      │           API GATEWAY              │  ── validates, authn/z, idempotency
                    │  - request validation              │  ── per-tenant + per-provider
                    │  - idempotency-key dedupe          │     RATE LIMITER (Redis token bucket)
                    │  - enqueue job, return 202+id      │
                    └───────┬───────────────────┬────────┘
                            │ write job (PENDING)│ enqueue
                            ▼                    ┊
                   ┌─────────────────┐           ┊ (async)
                   │   PostgreSQL    │◄──────────┊───────────┐
                   │  jobs           │           ▼           │ persist state transitions
                   │  job_events     │     ┌───────────────┐ │  (event sourcing)
                   │  providers      │     │  QUEUE        │ │
                   │  idempotency    │     │ (Redis Stream │ │
                   │  tenants/quota  │     │  / Kafka)     │ │
                   └───────▲─────────┘     └──────┬────────┘ │
                           │                      ┊ consume   │
                           │              ┌───────▼─────────────────────────┐
                           │              │        WORKER FLEET             │
       status/result ◄─────┘              │  - bounded concurrency pool      │
       (client polls /jobs/:id)           │  - state machine driver          │
                                          │  - HEALTH TRACKER (circuit       │
                                          │    breaker per provider)         │
                                          │  - RETRY (backoff+jitter)         │
                                          │  - FALLBACK chain                 │
                                          └───────┬──────────────┬──────────┘
                                                  │ call         │ call (fallback)
                                                  ▼              ▼
                                          ┌──────────┐   ┌──────────┐   ┌──────────┐
                                          │Provider A│   │Provider B│   │Provider C│   (mock LLM
                                          │ (model)  │   │ (model)  │   │ (model)  │    backends)
                                          └──────────┘   └──────────┘   └──────────┘

  OBSERVABILITY (cross-cutting): Prometheus metrics on gateway+workers, Loki logs w/ correlation_id,
  OpenTelemetry traces gateway→queue→worker→provider, Grafana SLO dashboards + alerts.
```

**Failure domains to mark on your own redraw:** Queue down (gateway can still accept? buffer? reject?), Postgres down (lose durability of new jobs?), one provider down (breaker opens, fail over), Redis down (rate limiter fail-open vs fail-closed), worker crash mid-job (visibility timeout → re-queue).

---

## 2. How each phase earns interview signal

| Phase | Machine Coding artifact | LLD artifact | HLD artifact |
|---|---|---|---|
| 0 — Harden the baseline | Idempotency middleware | Schema w/ constraints, indexes, **version column (OCC)** | Redraw the *single-service* baseline diagram correctly |
| 1 — Async jobs | Worker pool + **job state machine** | `jobs` + append-only `job_events` (event sourcing) | Add queue + worker boxes; sync vs async paths |
| 2 — Registry + routing | Selector strategies (weighted/least-loaded) | `providers` schema; persisted routing decisions | Control plane vs data plane split |
| 3 — Limits + health | **Rate limiter + circuit breaker + retry/fallback** | Redis atomic counters, breaker state, concurrency guards | Where state lives; Redis-down blast radius; scale math |
| 4 — Multi-tenancy | Per-tenant fairness / quota accounting | `tenants`, `api_keys`, `quotas`, usage **ledger** | Tenant isolation, noisy-neighbor blast radius |
| 5 — Storage lifecycle | Compaction job (bounded, resumable) | CQRS read model, snapshots, **compaction**, archival, expand-contract migration | Read/analytics path; data growth at scale |
| 6 — Platform capstone | Graceful shutdown / drain | — | **The "Exceptional (4)" diagram** + failure playbook + 10x/100x math |

You finish with: one running system + three deep, *honest* stories you can defend, because you built them.

---

## 3. The phases

> Each phase: **Goal → What you build → MC / LLD / HLD targets → Concepts to learn cold → Acceptance criteria → Interview rehearsal.** Treat acceptance criteria as your "definition of done" before moving on.

### Phase 0 — Harden the baseline (bridge from CRUD)
**Goal.** Make the existing service *clean and layered* so every later phase has a sane foundation. This is also your first taste of LLD discipline.

**What you build**
- Split the god-route into layers: `routes` (HTTP) → `services` (business logic) → `repositories` (DB access). Routes never touch `db.session` directly.
- Real input validation (pydantic v2 or marshmallow) — typed request/response models, not `if not all(key in data...)`.
- A central error handler → consistent error envelope `{error, code, request_id}` with proper HTTP status codes.
- **Correlation IDs:** middleware that reads/creates `X-Request-ID`, puts it in a context var, logs it on every line, returns it in the response. (Foundation for tracing later.)
- **Idempotent create:** `POST` accepts an `Idempotency-Key` header; replaying it returns the original result, not a duplicate.
- **Optimistic concurrency on update:** add a `version` column; `PUT` requires the client's expected version and rejects on mismatch (HTTP 409).

**MC target.** A small idempotency-key store + middleware (in-memory first, Redis later). Handle the race: two identical requests arrive concurrently — only one executes, the other waits and returns the same result (single-flight).

**LLD target.** Rewrite the schema properly:
```sql
CREATE TABLE students (
  id          BIGSERIAL PRIMARY KEY,
  name        VARCHAR(80)  NOT NULL,
  domain      VARCHAR(50)  NOT NULL,
  gpa         NUMERIC(3,2) NOT NULL CHECK (gpa >= 0 AND gpa <= 10),
  email       CITEXT       NOT NULL UNIQUE,
  version     INT          NOT NULL DEFAULT 1,        -- OCC guard
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_students_domain ON students(domain);

CREATE TABLE idempotency_keys (
  key          TEXT PRIMARY KEY,
  request_hash TEXT NOT NULL,        -- detect key reuse with a different body
  response     JSONB,
  status       SMALLINT NOT NULL,    -- 0=in-progress, 1=done
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL
);
```
The OCC update is the teachable moment:
```sql
UPDATE students SET gpa=$1, version=version+1, updated_at=now()
WHERE id=$2 AND version=$3;     -- 0 rows affected ⇒ conflict ⇒ 409
```

**HLD target.** Draw the *current* architecture honestly: client → nginx → gunicorn (N workers) → Flask → Postgres, with Prometheus scraping `/metrics`. Label protocols. This is your "level 2/3" warm-up before the system gets interesting.

**Concepts to learn cold:** layered architecture; optimistic vs pessimistic concurrency; idempotency keys; why `email` uniqueness alone isn't idempotency; HTTP status semantics (409, 422, 202).

**Acceptance criteria**
- [ ] No route function touches `db.session` directly.
- [ ] Replaying a `POST` with the same `Idempotency-Key` returns the *same* `id`, creates one row.
- [ ] Concurrent identical creates → one row (prove it with a script firing 50 parallel requests).
- [ ] `PUT` with a stale `version` returns 409.
- [ ] Every log line and error response carries `request_id`.

**Interview rehearsal.** *"Walk me through making a write endpoint safe under concurrent clients."* You should be able to say: validation → idempotency (dedupe retries) → OCC (dedupe conflicting updates) → and explain the difference between those two problems.

---

### Phase 1 — Async jobs + a state machine
**Goal.** Introduce work that *can't* finish in one request. This is where the system stops being CRUD.

**What you build**
- A long operation: e.g. `POST /jobs` `{type: "bulk_import", payload: {...}}` → `202 {job_id}`. (Bulk-import students, or "generate a cohort report" — pick one; the *type* is extensible.)
- A **queue** (start with Redis Streams — simplest durable queue; you'll justify Kafka vs SQS later).
- A **worker** process (separate entrypoint, separate container later) that consumes jobs and runs them.
- A **job state machine** with explicit, validated transitions.
- `GET /jobs/:id` → current state + result. `POST /jobs/:id/cancel`.

**MC target.** Two things:
1. A **bounded-concurrency worker pool** — N in-flight jobs max, backpressure when full. (Python: `asyncio.Semaphore` + task set, or a `ThreadPoolExecutor` with a bounded queue. Know the GIL implications and say them out loud.)
2. The **state machine** as code — a transition table that *rejects illegal transitions*:
```
PENDING ──► RUNNING ──► SUCCEEDED
   │           │   └────► FAILED ──► (retry) ──► PENDING
   └────► CANCELLED       │
                          └────► CANCELLED
```
Illegal (e.g. `SUCCEEDED → RUNNING`) raises. Transitions are the *only* way state changes.

**LLD target.** Event-sourced job state:
```sql
CREATE TABLE jobs (
  id            UUID PRIMARY KEY,
  tenant_id     UUID NOT NULL,
  type          TEXT NOT NULL,
  state         TEXT NOT NULL,              -- current (a projection of events)
  attempts      INT  NOT NULL DEFAULT 0,
  version       INT  NOT NULL DEFAULT 1,    -- OCC for the worker
  payload       JSONB NOT NULL,
  result        JSONB,
  idempotency_key TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_state ON jobs(state) WHERE state IN ('PENDING','RUNNING');

CREATE TABLE job_events (              -- append-only; the source of truth
  id        BIGSERIAL PRIMARY KEY,
  job_id    UUID NOT NULL REFERENCES jobs(id),
  seq       INT  NOT NULL,            -- per-job ordering
  type      TEXT NOT NULL,            -- ENQUEUED, STARTED, SUCCEEDED, FAILED, RETRIED, CANCELLED
  data      JSONB,
  at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (job_id, seq)
);
```
Worker updates use OCC (`WHERE id=? AND version=?`) so two workers can't both claim the same job. Talk about **at-least-once delivery** and why your job handlers must be **idempotent**.

**HLD target.** Add to the diagram: the queue box (dashed/async arrows), the worker fleet, the status-poll path. New failure domain: *worker dies mid-job* → visibility timeout / heartbeat → job re-queued. Draw it.

**Concepts to learn cold:** sync vs async API design (202 + polling vs webhooks vs SSE); at-least-once vs exactly-once vs at-most-once; idempotent consumers; visibility timeout / lease; event sourcing basics (events are truth, `state` is a cached projection); graceful cancellation.

**Acceptance criteria**
- [ ] `POST /jobs` returns 202 instantly; work happens in the worker.
- [ ] Illegal state transitions raise (unit-tested).
- [ ] Kill a worker mid-job → the job is picked up and completed by another worker (no lost work, no double-commit of side effects).
- [ ] Job state is reconstructable purely from `job_events`.
- [ ] Cancel transitions a `RUNNING` job to `CANCELLED` and the worker stops.

**Interview rehearsal.** *"Design a system to run long tasks submitted via an API."* You can now whiteboard submit→queue→worker→poll, explain delivery guarantees, and answer "what if a worker crashes?" with a real mechanism, not "it restarts."

---

### Phase 2 — Provider registry + smart routing
**Goal.** Jobs are dispatched to one of several *providers* (mock LLM backends / mock downstream services) chosen by a pluggable policy. Introduces control-plane vs data-plane thinking.

**What you build**
- A **registry**: providers with capabilities, weights, and limits, editable at runtime via a control-plane API — *no redeploy to add a provider.*
- A **selector** with swappable strategies: round-robin, weighted-random, least-loaded (fewest in-flight). Strategy chosen by config.
- Mock providers: small services (or in-process stubs) with configurable latency + failure rate, so you can *simulate* the real world for Phase 3.

**MC target.** The selector as a clean strategy interface:
```python
class Selector(Protocol):
    def pick(self, candidates: list[Provider], ctx: RouteContext) -> Provider | None: ...
```
Implement 3 strategies. Least-loaded needs a concurrency-safe in-flight counter per provider — first race condition to reason about out loud.

**LLD target.**
```sql
CREATE TABLE providers (
  id            UUID PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  model         TEXT NOT NULL,
  weight        INT  NOT NULL DEFAULT 1,
  rps_limit     INT  NOT NULL,            -- used in Phase 3
  max_inflight  INT  NOT NULL,
  enabled       BOOLEAN NOT NULL DEFAULT true,
  version       INT NOT NULL DEFAULT 1,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
Persist the routing decision on the job (`job_events` ROUTED event with provider_id) for debuggability — "why did this job go to provider B?"

**HLD target.** Split the diagram into **control plane** (registry/admin APIs, config) and **data plane** (gateway → queue → workers → providers). Mark that control-plane changes propagate to the data plane *without* a deploy. This is a strong senior signal.

**Concepts to learn cold:** control plane vs data plane; strategy pattern; config that changes behavior at runtime (and how workers learn about it — poll vs push/watch); why you persist routing decisions (observability/forensics).

**Acceptance criteria**
- [ ] Add/disable a provider via API → next jobs route accordingly within seconds, no restart.
- [ ] All three selector strategies pass tests, including the least-loaded concurrency case.
- [ ] Every completed job records which provider served it and why.

**Interview rehearsal.** *"How would you route requests across multiple backends?"* and *"How do you change behavior without redeploying?"* — you have a concrete answer with a registry + selector + control/data-plane separation.

---

### Phase 3 — Rate limiting, health tracking, retry + fallback  ⭐ (the MC showcase)
**Goal.** Protect providers, degrade gracefully. This is the single most interview-relevant phase — it's the Emergent "LLM request routing layer" problem almost verbatim.

**What you build**
- A **rate limiter**, two algorithms, per-provider and per-tenant:
  - **Token bucket** (smooths bursts, allows controlled burstiness).
  - **Sliding-window counter** (accurate windowed limits).
  - Distributed across workers via **Redis** (atomic `INCR`+`EXPIRE`, or a Lua script for true atomicity). Local in-memory version first to nail the algorithm, then make it distributed.
- A **health tracker = circuit breaker** per provider, a 3-state machine:
  ```
  CLOSED  ──(failures ≥ threshold)──►  OPEN
    ▲                                   │ (cooldown elapsed)
    │ (probe succeeds)                  ▼
    └────────────  HALF_OPEN  ◄─────────┘
                    │ (probe fails) ──► OPEN
  ```
- **Retry** with exponential backoff **+ jitter** and a max-attempts cap.
- **Fallback chain:** provider A fails / is OPEN / over-limit → try B → try C → finally fail the job with a meaningful error.
- **Thundering-herd mitigation:** jitter on retries; single-flight on identical in-flight work; half-open lets only *one* probe through.

**MC target.** This *is* the machine-coding round. You should be able to implement, from a blank file in ~45 min:
```python
class RateLimiter(Protocol):
    def allow(self, key: str, cost: int = 1) -> Decision: ...   # Decision(allowed, retry_after)

class CircuitBreaker:
    # states CLOSED/OPEN/HALF_OPEN; on_success(), on_failure(); allow_request() -> bool
    ...

def call_with_resilience(providers, request):  # retry + backoff+jitter + fallback + breaker
    ...
```
Be able to explain the **specific race** between "check the breaker" and "record the result" and how you make it safe.

**LLD target.** State lives in Redis (shared across workers):
```
ratelimit:{provider}:{window}    -> counter, TTL = window      (sliding window)
tokens:{provider}                -> token count + last-refill   (token bucket; Lua refill)
breaker:{provider}               -> {state, failures, opened_at} (atomic transitions)
```
Decide and *defend*: when Redis is down, does the limiter **fail open** (serve, risk overload) or **fail closed** (reject, stay safe)? There's no universally right answer — that's the point.

**HLD target.** On the diagram: mark Redis as a shared dependency and its blast radius. Add **scale math**: "At 5k jobs/s with 3 providers each capped at 2k rps, the limiter is the hot path — every job is ≥1 Redis round trip; at 5k rps that's fine for one Redis, at 200k rps I'd shard by provider / use local token buckets with periodic sync."

**Concepts to learn cold:** token bucket vs leaky bucket vs fixed/sliding window (tradeoffs of each); circuit breaker states + half-open probing; exponential backoff *why jitter matters* (correlated retries = thundering herd); fail-open vs fail-closed; distributed counters & atomicity (why `GET`+`SET` is a bug, why Lua/`INCR` isn't).

**Acceptance criteria**
- [ ] Under Locust load above a provider's limit, excess requests are shed or queued (not crashing the provider) and clients get `429`/`retry_after`.
- [ ] Forcing a provider to fail trips its breaker → traffic fails over to the next provider → breaker recovers via a half-open probe.
- [ ] Retries use backoff + jitter (prove with logged timestamps — they should *not* be evenly spaced).
- [ ] Rate-limit state is shared correctly across ≥2 worker processes (not per-process).
- [ ] You can articulate the fail-open/closed decision and have implemented one deliberately.

**Interview rehearsal.** This phase answers their literal practice prompt: *"Design an LLM request routing layer — model registry, rate limiter, health tracker, request pipeline."* You'll have built every component. Also rehearse implementing the rate limiter and breaker *from scratch, timed* — that's the MC round.

---

### Phase 4 — Multi-tenancy, quotas, auth
**Goal.** Multiple tenants share the platform without stepping on each other. Introduces fairness and isolation — classic senior-level concerns.

**What you build**
- **API keys** + tenant resolution on the gateway.
- **Per-tenant rate limits** and **quotas** (e.g., N jobs/day, or a credit balance debited per job).
- **Fairness:** one tenant's burst must not starve others (weighted fair queuing, or per-tenant queues with round-robin draining).
- A **usage ledger** (event-sourced) so billing/quota is auditable — never a single mutable counter.

**MC target.** Fair scheduling: given per-tenant queues, drain them so no tenant monopolizes the worker fleet. Implement and reason about starvation.

**LLD target.**
```sql
CREATE TABLE tenants (id UUID PK, name TEXT, plan TEXT, created_at TIMESTAMPTZ);
CREATE TABLE api_keys (
  id UUID PK, tenant_id UUID NOT NULL REFERENCES tenants(id),
  key_hash TEXT NOT NULL UNIQUE,           -- store a hash, never the key
  created_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ
);
CREATE TABLE usage_ledger (                -- append-only; balance = SUM(delta)
  id BIGSERIAL PK, tenant_id UUID NOT NULL,
  job_id UUID, delta NUMERIC NOT NULL,     -- +grant / -debit
  reason TEXT NOT NULL, at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ledger_tenant ON usage_ledger(tenant_id, at);
```
(You've seen this pattern in support work — credit ledgers, grant-then-debit. Use that intuition; it's exactly right.)

**HLD target.** Mark the **tenant isolation boundary** and **noisy-neighbor blast radius** on the diagram. Discuss: shared cluster vs cell-based isolation per tenant tier; where a runaway tenant is contained.

**Concepts to learn cold:** multi-tenancy models (shared / siloed / cell-based); fair queuing & starvation; quota as a ledger vs a counter (auditability, concurrent-debit safety); storing secrets as hashes; rate limiting as isolation, not just protection.

**Acceptance criteria**
- [ ] Auth required; revoked keys rejected.
- [ ] One tenant flooding the system does **not** stall another tenant's jobs (prove with a two-tenant Locust run).
- [ ] Quota enforced; balance derivable from the ledger; concurrent debits don't oversell (no balance < 0 race).

**Interview rehearsal.** *"How do you stop one customer's traffic from degrading everyone else?"* — fairness + isolation + quota, with a concrete fair-queue mechanism.

---

### Phase 5 — Storage lifecycle: CQRS, compaction, archival, online migration
**Goal.** The event log now grows without bound. This is the LLD-depth phase — storage efficiency and migration safety.

**What you build**
- A **read model (CQRS):** a denormalized `job_summary` table/projection optimized for the status/list queries, kept up to date from `job_events`. Reads stop scanning the event log.
- **Snapshots:** periodically snapshot a job's state so you don't replay thousands of events to rebuild it.
- **Compaction:** a background, *resumable, bounded* job that collapses/archives old `job_events` past a retention window.
- **Archival:** move cold jobs/events to object storage (S3/R2) with a pointer left behind; hot DB stays small.
- **Online migration:** add a column / change shape with **zero downtime** via expand-contract (add nullable → dual-write/backfill → switch reads → drop old).

**MC target.** The compaction worker: bounded batch size, resumable from a checkpoint, idempotent, and *safe to run while jobs are being written*. Handle the edge case: **compaction meets a concurrent state change** (don't compact a job that just transitioned).

**LLD target.** Define the read model + snapshot schema and the **migration runbook** as ordered steps. Be able to whiteboard the expand-contract sequence and answer "what if the backfill is half-done when you deploy?"

**HLD target.** Add the **analytics/read path** to the diagram (read replica or warehouse). Discuss data growth: "at 1M jobs/day, `job_events` grows ~XGB/day; retention 30d hot + archive; partition by day; compaction keeps the working set bounded."

**Concepts to learn cold:** CQRS (separate write model from read model); snapshotting & log compaction; partitioning (time-based) + TTL/archival; expand-contract / dual-write / backfill; *the interaction edge cases* — "rollback meets compaction," "migration meets concurrent writes." The guide calls these out specifically.

**Acceptance criteria**
- [ ] Status/list queries hit the read model, stay fast as `job_events` grows to millions of rows (measure).
- [ ] Job state reconstructable from snapshot + events after snapshot.
- [ ] Compaction is resumable (kill it mid-run, restart, no corruption, no double-archive).
- [ ] A schema change deployed with zero downtime, documented as an expand-contract runbook.

**Interview rehearsal.** Emergent's literal LLD prompts: *"versioned document store with OCC, rollback, and compaction"* and *"chat message storage… token-budget retrieval."* You'll have done event sourcing, OCC, snapshots, compaction, and online migration — answer all of them from real experience.

---

### Phase 6 — Platform capstone (HLD + your DevOps, unified)
**Goal.** Wire the new architecture into the platform you *already* built, and produce the interview-ready HLD package.

**What you build / wire up**
- **Two deployables:** `gateway` and `worker` as separate images, separate Helm releases (you already have the chart patterns).
- **Autoscaling on the right signal:** HPA on **queue depth / job backlog** (custom metric via Prometheus Adapter) — not just CPU. This is the senior move; explain *why* CPU is the wrong signal for a queue-backed system.
- **Progressive delivery:** canary or blue-green the gateway via Argo Rollouts; workers drain in-flight jobs before terminating (graceful shutdown / `preStop` + `SIGTERM` handling).
- **SLOs on the new golden signals:** request p99, **queue depth, breaker-open rate, retry rate, job age**. Alerts in your existing Prometheus/Alertmanager.
- **Distributed tracing:** OpenTelemetry, propagate `correlation_id` from gateway → queue → worker → provider; view a full trace in Grafana/Tempo.

**MC target.** Graceful shutdown / drain logic in the worker: stop pulling new jobs, finish in-flight (up to a deadline), re-queue the rest, exit clean.

**HLD target — the deliverable that gets you the offer.** Produce the **"Exceptional (4)"** diagram (per the guide's rubric): all components, labeled protocols, **failure domains marked, sync vs async distinguished, control vs data plane, scale boundaries identified, the bottleneck called out.** Plus two written one-pagers:
1. **Failure playbook — "what breaks at 3am":** for each component (queue, Postgres, Redis, a provider, a worker), the symptom, blast radius, and recovery. (This is your home turf — lean into the SRE strength.)
2. **Scale at 10x / 100x:** concrete numbers — current bottleneck, what saturates first, what you'd change (shard Redis, partition Postgres, Kafka over Redis Streams, multi-region).

**Concepts to learn cold:** autoscaling on custom/queue metrics; graceful shutdown & connection draining; progressive delivery (canary vs blue-green tradeoffs); golden signals for a queue-backed async system; distributed tracing & context propagation; SLO/SLI/error budgets.

**Acceptance criteria**
- [ ] Gateway and worker deploy independently; worker scales on backlog, not CPU.
- [ ] A rolling deploy of workers loses zero in-flight jobs.
- [ ] One full request traced end-to-end across all hops.
- [ ] Dashboards + alerts exist for all five golden signals.
- [ ] The "Exceptional (4)" diagram + both one-pagers are written and you can present each in <10 min.

**Interview rehearsal.** This is your HLD round, fully loaded: draw first, talk second; answer every "what happens when X dies?" from your playbook; give scale numbers, not adjectives.

---

## 4. Diagram practice protocol (HLD round is diagram-first)

The guide makes the **architecture diagram mandatory and graded 1–4.** Practice the *act of drawing*, not just the design:

1. **Tool:** Excalidraw (matches whiteboard-style). Pen+paper on camera is fine as backup.
2. **Order, every time:** boxes (components) → arrows (who calls whom) → label every arrow with protocol (HTTP/gRPC/Redis/Kafka) → solid=sync, dashed=async → group into planes → mark failure domains → circle the bottleneck.
3. **The 20-minute drill:** after each phase, redraw the *whole current system* from a blank canvas in 20 minutes, narrating aloud. Time yourself. By Phase 6 you can draw the full platform in one pass — that's the "tells the story without words" bar.
4. **Self-grade against the rubric** in the guide (Weak 1 → Exceptional 4) after each drill.

---

## 5. Turn the project into mock interviews

The project is the *source material*; these drills convert it into round-ready reps:

- **MC drill (weekly):** open a blank file, set a 45-min timer, re-implement *one* component from scratch — rate limiter, circuit breaker, state machine, worker pool, fair scheduler. Narrate the plan for the first 5 min (the guide rewards this), then code. No copy-paste from your repo.
- **LLD drill:** pick one Emergent prompt (versioned doc store / chat storage / routing layer), and in 50 min produce: DDL with indexes + constraints, interface signatures with types and error cases, one sequence diagram, and a concurrent-access walkthrough. Compare to what you actually built.
- **HLD drill:** the 20-min diagram drill above + 30 min of self-asked follow-ups ("what breaks when Redis dies?", "10x scale?", "why Redis Streams not Kafka?").
- **Think-aloud habit:** record yourself once. The guide says "silence is a missed signal" — verify you're narrating *why before what*.

---

## 6. Defensible tech-choice cheat sheet

Have a one-line *reason* for every choice (the guide penalizes name-dropping). Examples you'll be able to defend because you built them:

| Decision | Pick | Defense (the "why", and the alternative you rejected) |
|---|---|---|
| Queue | **Redis Streams** → Kafka later | Streams: durable, consumer groups, simple ops — right for <50k msg/s. Kafka when you need partitioned ordering, replay, or >100k/s. SQS if you want zero-ops managed + don't need ordering. |
| Limiter store | **Redis** atomic ops | Shared across workers; `INCR`/Lua is atomic. In-process won't enforce a global limit across N workers. |
| Job source of truth | **Event log** (`job_events`) | Auditable, reconstructable, enables CQRS. A single mutable `state` column loses history and races. |
| Concurrency control | **OCC (version)** for jobs | Low contention, no lock held across a network call. Pessimistic locks would block the worker pool. |
| Limiter algorithm | **Token bucket** (default) | Allows controlled bursts; sliding window when you need strict windowed accuracy. Fixed window has the boundary-burst bug. |
| Autoscale signal | **Queue depth** | CPU lags for I/O-bound queue consumers; backlog is the true demand signal. |
| Datastore | **Postgres** (jobs) + **Redis** (limits/cache) | Relational integrity + transactions for jobs; Redis for hot atomic counters. Not Mongo — you need constraints and joins for tenancy/quota. |

---

## 7. Suggested cadence (adjust to your time)

Part-time, ~8–10 focused hrs/week:

| Weeks | Phase | Primary round it builds |
|---|---|---|
| 1 | Phase 0 — harden | LLD foundations |
| 2–3 | Phase 1 — async + state machine | MC + LLD + HLD |
| 4 | Phase 2 — registry + routing | HLD (planes) + MC |
| 5–6 | Phase 3 — limits/health/retry ⭐ | MC (the big one) + LLD |
| 7 | Phase 4 — multi-tenancy | LLD + HLD |
| 8 | Phase 5 — storage lifecycle | LLD depth |
| 9–10 | Phase 6 — platform capstone | HLD capstone + your SRE strength |

Don't skip ahead — each phase's acceptance criteria are the prerequisite for the next. Phase 3 is the highest-value; if time is tight, do 0→1→3 well rather than all of them shallowly. **Depth over breadth** is literally what they say they value.

---

## 8. Definition of done (your portfolio)

When this is finished you have, all in one repo:
- A running distributed system (gateway + workers + queue + Postgres + Redis + providers).
- Your existing platform stack (Helm/Argo/Terraform/observability) wrapping something real.
- Three rehearsed, *honest* stories — MC components you can re-code blind, LLD schemas you designed, an HLD diagram you can draw in 20 minutes.
- A failure playbook and a scale-math one-pager.
- A README that frames it as: *"async job-orchestration / LLM-gateway platform — here's the architecture, here's what breaks and how I designed for it, here's how it scales."*

That last paragraph is the resume line that makes a DevOps profile read as a systems engineer. That's the goal.
