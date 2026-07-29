# Cloud Solution Architect — Reference Library & CSA Study Companion

> **⚠️ Status (updated 2026-06-30):** The authoritative spine is now **`MASTER-BUILD-PROGRAM.md`** — the full 6–12 month, 12-stage "build everything" program. The original 2-month / 8-week framing below is a *compressed subset* of it. This document is **retained and still valid** for its **reference library (§4), local-build tiers (§8–9), CSA muscle/subject framing (§0, §2), and cloud-service mapping (§1)**. Where §3's schedule says "8 weeks," map it onto **Stages 0–6** of the master program.
>
> **Goal.** Build the knowledge a **Cloud Solution Architect (CSA)** is hired for. You write 100% of the code — this document is concepts + what to refer to *before* you build each part. **No code here.**

---

## 0. What a Cloud Solution Architect is actually assessed on

A CSA is not "a senior engineer who knows AWS." The role is judged on six muscles. Our project is engineered to exercise every one:

| CSA muscle | What it means | Where this project proves it |
|---|---|---|
| **Service selection** | Pick the right managed service and *defend it vs. alternatives* | Queue, DB, cache, compute, secrets — each chosen with a written tradeoff |
| **Well-Architected design** | Reason across reliability, security, cost, performance, ops, sustainability | A self-run Well-Architected review of your own system (Week 8) |
| **Failure & blast-radius thinking** | "What breaks, how far does it spread, how do we recover?" | Failure playbook + multi-AZ/region DR design |
| **Cost awareness** | Architecture has a bill; right-size and model it | A cost model + FinOps pass on your design |
| **Security & compliance** | IAM, network isolation, encryption, least privilege, data residency | Auth, secrets, VPC/network design, encryption in transit/at rest |
| **Communication** | Diagrams, ADRs, design docs a stakeholder can read | Architecture diagram (graded), 5+ ADRs, a design doc, a runbook |

Keep this table visible. Every week you should be able to point at what you produced for each muscle.

---

## 1. The system, at architecture level (no code)

**"Helios" — an async job-orchestration platform / LLM gateway.** Clients submit *jobs* (an LLM completion, a bulk import, a report — any work too slow for one request cycle). The platform accepts the job instantly, routes it to a healthy provider under rate-limit constraints, processes it on a worker fleet with retries and fallback, tracks every state change durably, and exposes status, results, quotas, and metrics.

### Components & planes (what you'll design)
- **API Gateway (data plane):** validation, authn/z, idempotency, enqueue, return "accepted + id". Hosts the rate limiter.
- **Queue:** durable buffer between accept and process (async boundary).
- **Worker fleet (data plane):** consumes jobs, drives the state machine, calls providers with resilience (retry/backoff/fallback), respects the circuit breaker.
- **Provider registry (control plane):** the set of backends, their weights and limits, editable at runtime — no redeploy.
- **Tenant/admin API (control plane):** tenants, API keys, quotas.
- **Datastores:** a relational store for jobs/events/tenants (durability + integrity); an in-memory store for rate-limit counters and breaker state (atomic, hot).
- **Object storage:** archived/cold job history.
- **Observability plane:** metrics, logs with correlation IDs, distributed traces, SLO dashboards, alerts.

### Data you'll model (described, not coded)
- **Job:** identity, tenant, type, current state, attempt count, an **optimistic-concurrency version**, payload, result, idempotency key, timestamps.
- **Job event (append-only):** the source of truth; ordered per job; one row per state transition.
- **Provider:** identity, model, weight, rate limit, max in-flight, enabled flag, version.
- **Tenant / API key / quota / usage ledger (append-only):** auth + fair-use accounting.
- **Rate-limit & breaker state:** hot, atomic, shared across workers (in the in-memory store, not per-process).

### Cloud-service mapping (the CSA exercise — know the equivalents and when to pick each)
| Role in Helios | AWS | Azure | GCP | When you'd pick it |
|---|---|---|---|---|
| Async queue | SQS / MSK (Kafka) | Service Bus / Event Hubs | Pub/Sub / Managed Kafka | SQS/Pub-Sub when you want zero-ops + don't need partition-ordering or replay; Kafka when you need ordered partitions, replay, high throughput |
| Hot counters / cache | ElastiCache (Redis) | Azure Cache for Redis | Memorystore | Atomic counters, leaderboards, ephemeral state |
| Relational store | RDS / Aurora | Azure Database for PostgreSQL | Cloud SQL / AlloyDB | Transactions, constraints, joins (tenancy, ledger) |
| Container compute | EKS / ECS / Fargate | AKS / Container Apps | GKE / Cloud Run | EKS when you already run k8s (you do); serverless-container (Fargate/Cloud Run) to cut ops |
| Object storage | S3 | Blob Storage | Cloud Storage | Cheap durable cold archive |
| Secrets | Secrets Manager / Param Store | Key Vault | Secret Manager | Rotate, audit, least-privilege access |
| CDN / edge | CloudFront | Front Door / CDN | Cloud CDN | Static/edge caching, TLS termination, WAF |
| Load balancer | ALB / NLB | App Gateway / Load Balancer | Cloud Load Balancing | L7 routing (ALB) vs L4 throughput (NLB) |
| Observability | CloudWatch / X-Ray + Managed Prometheus/Grafana | Monitor / App Insights | Cloud Monitoring / Trace | Metrics, traces, logs, SLOs |

> **Do this for real:** pick **one** cloud as primary (AWS is the most common CSA hiring target), and for every component write one sentence: *"I chose X over Y because Z."* That habit is 50% of the CSA interview.

---

## 2. Everything we will learn — the complete subject catalog

Fifteen domains. This is the "deep subjects" coverage. You won't master all of it in 8 weeks, but you'll *touch every one through the build* and know what to read next.

**A. Architecture & design thinking** — architectural styles (layered, hexagonal/ports-&-adapters, microservices, event-driven); the 12-Factor App; coupling/cohesion; bounded contexts; API design (REST maturity, versioning, pagination, idempotency); ADRs & tradeoff analysis; the Well-Architected mindset.

**B. Distributed systems theory** — CAP & PACELC; consistency models (strong, eventual, causal, read-your-writes); the fallacies of distributed computing; logical/physical clocks & ordering; consensus (Raft) at a conceptual level; quorums; idempotency & exactly-once *illusion*; partial failure.

**C. Asynchronous & event-driven systems** — sync vs async API design (polling, webhooks, SSE/streaming); message queues vs logs vs streams; delivery semantics (at-most/at-least/exactly-once); competing consumers; queue-based load leveling; dead-letter queues; backpressure; ordering & partitioning; event sourcing & CQRS; sagas / distributed transactions.

**D. Resilience & reliability engineering** — timeouts, retries, **exponential backoff + jitter**; circuit breaker; bulkhead; rate limiting & load shedding; throttling; graceful degradation & fallback; thundering herd & single-flight; shuffle-sharding; static stability; health checks (liveness/readiness/deep); chaos engineering.

**E. Data systems & storage** — relational vs document vs key-value vs wide-column vs graph vs time-series (and *why* each); indexing & query planning; normalization vs denormalization; partitioning/sharding strategies; replication (leader-follower, multi-leader, leaderless); read replicas; optimistic vs pessimistic concurrency; storage engines (B-tree vs LSM); compaction; online schema migration (expand-contract / dual-write / backfill); backup/restore, PITR; data lifecycle, TTL, archival, tiering.

**F. Cloud platform & Well-Architected** — the 6 pillars (Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability); regions/AZs; managed vs self-hosted tradeoffs; serverless vs containers vs VMs; the shared-responsibility model; landing zones & account/subscription structure; service quotas & limits.

**G. Networking** — VPC/VNet, subnets (public/private), route tables; security groups vs NACLs; NAT, internet/egress gateways; load balancing L4 vs L7; DNS & service discovery; private connectivity (PrivateLink/Private Endpoints/peering); CDN & edge; TLS termination; WAF; ingress/egress control; the OSI layers you actually use.

**H. Security, identity & compliance** — IAM (roles, policies, least privilege, assume-role); AuthN vs AuthZ; OAuth2 / OIDC / JWT; API keys & rotation; secrets management & encryption (KMS, envelope encryption, at-rest & in-transit); zero-trust; network isolation as security; data residency/sovereignty; OWASP Top 10; audit logging; the principle of least privilege everywhere.

**I. Containers & orchestration** — images & layering; OCI; Kubernetes objects (pod/deployment/service/ingress/configmap/secret); requests/limits & QoS; HPA / VPA / cluster autoscaler; custom-metric autoscaling; probes; rolling/canary/blue-green; pod disruption budgets; graceful shutdown (SIGTERM/preStop/draining); operators; service mesh basics.

**J. Infrastructure as Code & GitOps** — declarative vs imperative; Terraform (state, modules, workspaces, drift, remote backends); Helm (templating, values, releases); GitOps (Argo CD) reconciliation loop; immutable infra; environment promotion; policy-as-code (OPA/Conftest) at a concept level.

**K. Observability & SRE** — the three pillars (metrics, logs, traces); RED & USE methods; the four golden signals; SLI/SLO/SLA & error budgets; structured logging & correlation IDs; distributed tracing & context propagation (OpenTelemetry); cardinality; alerting on symptoms not causes; runbooks; on-call & incident response; postmortems.

**L. Cost optimization / FinOps** — pricing models (on-demand, reserved/savings plans, spot); right-sizing; storage tiering; data-transfer/egress cost (the silent killer); tagging & cost allocation; unit economics ($/job); autoscaling for cost; build-vs-buy economics; the FinOps lifecycle (inform/optimize/operate).

**M. Scalability & performance** — vertical vs horizontal scaling; statelessness; caching strategies (cache-aside, write-through, TTL, invalidation); connection pooling; the bottleneck mindset; capacity planning & queueing theory basics (Little's Law); latency vs throughput; tail latency (p99) & why averages lie; load testing.

**N. Disaster recovery & business continuity** — RTO/RPO; the DR strategy ladder (backup-&-restore → pilot light → warm standby → active-active multi-region); multi-AZ vs multi-region; failover & failback; data replication for DR; static stability during AZ loss; backup testing (untested backups = no backups).

**O. Architecture communication & documentation** — the C4 model (context/container/component/code); the "Exceptional-4" diagram bar (failure domains, sync/async, control/data plane, scale boundaries, bottleneck marked); ADRs; design docs / RFCs; sequence diagrams; presenting to technical *and* non-technical stakeholders; whiteboarding live.

---

## 3. The 8-week plan

> Each week: a **build milestone** (you code it) + the **subjects** that milestone teaches + **what to refer before you start.** Assumes ~12–15 focused hrs/week. The build follows `SCALING-ROADMAP.md` phases; this layers the CSA study on top.

### Week 1 — Architecture foundations + harden the baseline (Phase 0)
- **Build:** layer the existing app (HTTP → service → repository), add validation, a consistent error model, correlation IDs, idempotent create, optimistic-concurrency updates.
- **Subjects:** A (architecture styles, 12-Factor, API/idempotency), early E (OCC), the Well-Architected mindset (F).
- **Refer before building:**
  - *The Twelve-Factor App* (12factor.net) — read all 12, free.
  - *Fundamentals of Software Architecture* — Richards & Ford — Ch. 1–6 (styles, components, characteristics).
  - Microsoft **Cloud Design Patterns** catalog (Azure Architecture Center) — read *Idempotency*, *Health Endpoint Monitoring*. (Vendor-neutral, free, and the single most useful pattern catalog for this whole project — bookmark it.)
  - AWS / Azure / GCP **Well-Architected Framework** overview — read the 6-pillar summary once for orientation.

### Week 2 — Async & distributed fundamentals + jobs/queue/state machine (Phase 1)
- **Build:** job submission returns "accepted", a durable queue, a worker that consumes, an explicit job state machine, append-only event log (event sourcing), at-least-once + idempotent consumer.
- **Subjects:** B (CAP, consistency, partial failure, idempotency), C (queues, delivery semantics, event sourcing/CQRS, DLQ, backpressure).
- **Refer:**
  - *Designing Data-Intensive Applications* (Kleppmann) — **Ch. 1 (reliability/scalability/maintainability), Ch. 5 (replication), Ch. 9 (consistency & consensus, conceptual).** This book is the spine of distributed-systems literacy — start it now, it carries you through Week 6.
  - Cloud Design Patterns: *Queue-Based Load Leveling*, *Competing Consumers*, *Priority Queue*, *Event Sourcing*, *CQRS*, *Saga*.
  - Martin Fowler — *Event Sourcing* and *CQRS* articles (martinfowler.com, free).
  - "Fallacies of Distributed Computing" — read the 8 fallacies (any summary).

### Week 3 — Routing & control/data plane + registry/selection (Phase 2)
- **Build:** runtime-editable provider registry; pluggable selection strategies (round-robin, weighted, least-loaded); persist the routing decision.
- **Subjects:** A (control vs data plane), D (intro to resilience), M (load-balancing algorithms, statelessness).
- **Refer:**
  - *Building Microservices* (Sam Newman, 2nd ed.) — service decomposition, integration, service discovery.
  - microservices.io (Chris Richardson) — *Service Registry*, *Client/Server-side discovery*, *Strangler Fig* patterns.
  - Cloud Design Patterns: *Gateway Routing*, *Gateway Aggregation*, *Ambassador*, *Sidecar*.
  - Load-balancing algorithms primer (round-robin vs least-connections vs weighted vs power-of-two-choices) — any reputable write-up; understand power-of-two-choices.

### Week 4 — Resilience deep dive + rate limiting / circuit breaker / retry-fallback (Phase 3) ⭐
- **Build:** token-bucket + sliding-window rate limiter (shared across workers, atomic), circuit breaker (closed/open/half-open), retry with backoff + jitter, fallback chain, load shedding.
- **Subjects:** D (the entire domain), C (backpressure), M (tail latency).
- **Refer (this is the richest reading week):**
  - *Release It!* (Michael Nygard, 2nd ed.) — **the stability-patterns chapters: Circuit Breaker, Bulkhead, Timeouts, Steady State, Fail Fast, Load Shedding.** This is THE book for this phase.
  - **Amazon Builders' Library** (aws.amazon.com/builders-library, free) — read these four: *"Timeouts, retries and backoff with jitter"* (Marc Brooker), *"Using load shedding to avoid overload,"* *"Avoiding insurmountable queue backlogs,"* *"Avoiding fallback in distributed systems."*
  - Cloud Design Patterns: *Retry*, *Circuit Breaker*, *Throttling*, *Bulkhead*, *Rate Limiting*.
  - Rate-limiting algorithm deep-dives — Stripe and Cloudflare both have well-known engineering posts on token bucket vs sliding window; read one of each. Understand why fixed-window has a boundary-burst bug.
  - DDIA — revisit the timeouts/unreliable-networks section of Ch. 8.

### Week 5 — Security, identity, networking + multi-tenancy (Phase 4)
- **Build:** API-key auth + tenant resolution, per-tenant rate limits + quotas, fair scheduling (no starvation), usage ledger.
- **Subjects:** H (IAM, OAuth2/OIDC/JWT, secrets, encryption, zero-trust), G (VPC, subnets, SG/NACL, LB, PrivateLink, CDN, WAF), D (shuffle-sharding for isolation).
- **Refer:**
  - Well-Architected **Security pillar** (your chosen cloud) — read it end to end.
  - Your cloud's **networking fundamentals** docs — VPC/VNet, subnets, security groups vs NACLs, NAT, load balancer types, PrivateLink/Private Endpoints. (AWS VPC docs / Azure Virtual Network docs / GCP VPC docs.)
  - OAuth 2.0 & OpenID Connect — oauth.net + the OIDC spec intro; understand the difference and where JWTs fit.
  - OWASP Top 10 (current edition) — read the list and the API Security Top 10.
  - Amazon Builders' Library — *"Workload isolation using shuffle-sharding"* (tenant isolation / blast-radius).
  - Cloud Design Patterns: *Gatekeeper*, *Valet Key*, *Throttling* (multi-tenant), *Federated Identity*.

### Week 6 — Data at scale + CQRS/compaction/migration (Phase 5)
- **Build:** a read model (CQRS) for status queries, snapshots, a resumable compaction job, archival to object storage, a zero-downtime expand-contract migration.
- **Subjects:** E (full domain — partitioning, replication, storage engines, compaction, online migration, lifecycle), N (backup/PITR, RTO/RPO intro).
- **Refer:**
  - DDIA — **Ch. 3 (storage & retrieval — B-tree vs LSM), Ch. 6 (partitioning), Ch. 7 (transactions), Ch. 11 (stream processing).**
  - *Database Internals* (Alex Petrov) — Part I (storage engines) for depth on LSM/compaction.
  - Online schema migration: read about the **expand-contract / parallel-change** pattern (Martin Fowler's *ParallelChange* / *blue-green data* writings; GitHub's `gh-ost` and Stripe's online-migration blog posts are excellent real-world references).
  - Cloud Design Patterns: *Materialized View*, *Sharding*, *Cache-Aside*, *Index Table*.

### Week 7 — Cloud-native ops, scale, DR, multi-region (Phase 6)
- **Build:** split gateway/worker into independent deployables, autoscale workers on **queue depth** (custom metric), progressive delivery, graceful drain, SLO dashboards + alerts on golden signals, distributed tracing end-to-end.
- **Subjects:** I (HPA/custom metrics, probes, graceful shutdown, canary/blue-green), K (golden signals, SLO/error budgets, OpenTelemetry, tracing), N (DR ladder, multi-AZ vs multi-region, static stability).
- **Refer:**
  - **Google SRE Book** + **SRE Workbook** (sre.google/books, free) — SLI/SLO/error budgets, monitoring, eliminating toil, incident response.
  - Kubernetes docs — HPA (incl. custom/external metrics), Pod lifecycle & termination, PodDisruptionBudget, probes.
  - OpenTelemetry docs (opentelemetry.io) — concepts: traces, spans, context propagation, the collector.
  - Amazon Builders' Library — *"Implementing health checks,"* *"Static stability using Availability Zones,"* *"Ensuring rollback safety during deployments,"* *"Going faster with continuous delivery."*
  - Well-Architected **Reliability** + **Operational Excellence** pillars — the DR strategy ladder (backup-restore → pilot light → warm standby → active-active) lives here.

### Week 8 — Cost, Well-Architected review, capstone artifacts + interview polish
- **Build/produce (no new features — you *document and review*):**
  - A **Well-Architected review** of your own system across all 6 pillars (find your own gaps).
  - A **cost model**: estimate monthly $ at a chosen scale; identify the top cost driver and one optimization.
  - The **"Exceptional-4" architecture diagram** (failure domains, sync/async, control/data plane, scale boundaries, bottleneck).
  - **5+ ADRs** (queue choice, datastore choice, limiter algorithm, fail-open vs fail-closed, autoscale signal).
  - A **failure playbook** ("what breaks at 3am") and a **scale-at-10x/100x** one-pager.
- **Subjects:** L (FinOps — pricing models, right-sizing, egress, tagging, unit economics), F (sustainability pillar), O (C4 diagrams, ADRs, design docs, stakeholder communication).
- **Refer:**
  - *Cloud FinOps* (O'Reilly — Storment & Fuller) — pricing models, allocation, the FinOps lifecycle.
  - Your cloud's **pricing calculator** — model Helios for real.
  - The **C4 model** (c4model.com, free) — for clean, leveled diagrams.
  - ADR format — Michael Nygard's original "Documenting Architecture Decisions" + the `adr` GitHub templates.
  - Well-Architected **Cost Optimization** + **Sustainability** pillars.
  - *Software Architecture: The Hard Parts* (Ford, Richards et al.) — for tradeoff-analysis vocabulary you'll use in ADRs and interviews.

---

## 4. The reference library (everything, in one place)

**Core books (buy/borrow these three first):**
- *Designing Data-Intensive Applications* — Martin Kleppmann. The distributed-data bible.
- *Release It!* (2nd ed.) — Michael Nygard. Resilience/stability patterns.
- *Fundamentals of Software Architecture* — Mark Richards & Neal Ford. How to think like an architect.

**Next tier:**
- *Building Microservices* (2nd ed.) — Sam Newman.
- *Software Architecture: The Hard Parts* — Ford, Richards, Sadalage, Dehghani.
- *Database Internals* — Alex Petrov.
- *Cloud FinOps* — Storment & Fuller.
- *System Design Interview* Vol 1 & 2 — Alex Xu (for interview framing).
- *Designing Distributed Systems* — Brendan Burns (cloud-native patterns).

**Free online books:**
- Google **SRE Book** & **SRE Workbook** — sre.google/books.
- **The Twelve-Factor App** — 12factor.net.
- **Amazon Builders' Library** — aws.amazon.com/builders-library (dozens of free, battle-tested articles; the most directly relevant reading for this entire project).

**Pattern catalogs (free, bookmark all):**
- **Microsoft Cloud Design Patterns** — Azure Architecture Center. Vendor-neutral, maps 1:1 to what you're building.
- **microservices.io** — Chris Richardson's pattern language.
- **martinfowler.com** — Event Sourcing, CQRS, CircuitBreaker, StranglerFig, ParallelChange, BlueGreenDeployment.
- **Well-Architected Frameworks** — AWS, Azure, and GCP each publish theirs; read your primary cloud's in full, skim the others to compare.

**Must-read classics / papers (conceptual, skim for the ideas):**
- "Fallacies of Distributed Computing" (Deutsch/Gosling).
- Lamport — "Time, Clocks, and the Ordering of Events."
- **Raft** — "In Search of an Understandable Consensus Algorithm" + the visualization at raft.github.io.
- Amazon **Dynamo** paper (eventual consistency, quorums).
- Google **Dapper** paper (distributed tracing — underpins OpenTelemetry).
- Jeff Dean — "Latency Numbers Every Programmer Should Know."

**Courses / channels:**
- **MIT 6.824 Distributed Systems** — lectures public on YouTube (the gold standard, free).
- **ByteByteGo** (Alex Xu) — system-design visual explainers.
- Your cloud's free training: **AWS Skill Builder** / **Microsoft Learn** / **Google Cloud Skills Boost**.

**Certifications (optional but high-ROI for a CSA target in 8 weeks):**
- **AWS Certified Solutions Architect – Associate (SAA-C03)** — the single most recognized CSA credential; achievable in this window and it *forces* the service-selection breadth a CSA needs. Pair the study with the build.
- Alternatives by cloud: **Azure AZ-305** (Designing Azure Infrastructure Solutions), **Google Professional Cloud Architect**.
- Optional credibility add-on: **CKA** (Certified Kubernetes Administrator) — you're already most of the way there from your existing stack.

---

## 5. The pattern catalog → where it lives in your build

Use this to connect "a pattern I read about" to "a thing I built" — that linkage is what makes interview answers land.

| Pattern | Built in | One-line "why" you'll defend |
|---|---|---|
| Queue-Based Load Leveling | Phase 1 | Decouple spiky intake from steady processing |
| Competing Consumers | Phase 1 | Scale throughput by adding workers |
| Event Sourcing / CQRS | Phase 1 / 5 | Auditable truth + fast reads |
| Saga (compensation) | Phase 1 (discuss) | Undo multi-step work without distributed txns |
| Strategy (selector) | Phase 2 | Swap routing policy without touching callers |
| Control vs Data Plane | Phase 2 | Change behavior with no redeploy |
| Retry + Backoff + Jitter | Phase 3 | Recover from transient faults without thundering herd |
| Circuit Breaker | Phase 3 | Stop hammering a dead dependency; fail fast |
| Bulkhead / Shuffle-Sharding | Phase 3 / 4 | Contain blast radius; isolate tenants |
| Throttling / Rate Limiting | Phase 3 | Protect backends; enforce fairness |
| Load Shedding | Phase 3 | Stay up under overload by dropping excess |
| Gatekeeper / Valet Key | Phase 4 | Validate at the edge; scope credentials tightly |
| Materialized View / Cache-Aside | Phase 5 | Keep reads fast as data grows |
| Sharding / Partitioning | Phase 5 | Scale storage past one node |
| Expand-Contract (Parallel Change) | Phase 5 | Migrate schema with zero downtime |
| Health Endpoint Monitoring | Phase 6 | Let the platform detect & route around sickness |
| Static Stability | Phase 6 | Survive an AZ loss without control-plane dependency |

---

## 6. How to make it stick (and convert to interview reps)

- **Read *before* you build, not after.** Each week's "refer" list is a prerequisite, not a footnote. Read the pattern, then implement it — you'll implement it better and remember why.
- **Write an ADR for every real decision** as you go (don't batch them to Week 8). One page: context, options, decision, consequences. By the end you have a portfolio *and* rehearsed tradeoff answers.
- **Keep a "why" sentence per technology.** A CSA who can't say "X over Y because Z" fails the interview regardless of the build.
- **Diagram drill (weekly):** redraw the whole current system from blank in 20 minutes, narrating. Self-grade against the Exceptional-4 bar. By Week 7 it's one fluid pass.
- **Teach-back:** after each week, explain that week's hardest concept out loud as if to a stakeholder. If you can't, you haven't learned it yet.
- **Mock the rounds in the last 2 weeks:** one HLD whiteboard (draw + defend failures + scale), one LLD design (data model + interfaces in prose + concurrency walkthrough), one "machine-coding" component re-built from scratch on a timer (rate limiter or circuit breaker). The guide rewards thinking aloud — practice narrating *why before what*.

---

## 7. Definition of done (your CSA portfolio after 8 weeks)

A running cloud-native platform, plus the artifacts that get a CSA hired:
- [ ] **Architecture diagram** at the Exceptional-4 bar (failure domains, sync/async, control/data plane, scale boundaries, bottleneck).
- [ ] **Cloud-service-selection table** with a defended "why" per component.
- [ ] **5+ ADRs** capturing real tradeoffs.
- [ ] **Well-Architected self-review** across all 6 pillars, with identified gaps.
- [ ] **Cost model** + one optimization, with unit economics ($/job).
- [ ] **Security & network design** (IAM least-privilege, isolation, encryption, secrets).
- [ ] **DR design** with stated RTO/RPO and a strategy on the ladder.
- [ ] **Failure playbook** + **10x/100x scale** one-pager.
- [ ] A **README/design doc** that frames the whole thing for a stakeholder.

That set — a real system *plus* the architect's paper trail explaining and justifying it — is exactly what a Cloud Solution Architect interview is looking for, and it's the resume line that separates "DevOps engineer" from "architect."

---

## 8. Local vs Cloud build matrix (per phase)

**The headline:** ~90% of Helios builds and runs on this laptop (10 cores / 16 GB / ~78 GB free) for free. The cloud-only pieces are *designed and modeled* locally, then ideally *touched once* on a real cloud in Week 7. "Simulated locally" means you learn the **pattern** faithfully but not the managed service's real SLA/behavior.

| Phase | Runs 100% local (free) | Simulated locally (concept only) | What a real cloud adds |
|---|---|---|---|
| **0 — Harden** | App + Postgres via Docker Compose; validation, idempotency, OCC | — (nothing cloud-specific) | Nothing yet |
| **1 — Async / queue / state machine** | Redis (Streams) as the queue; worker; event log — all in Compose | Managed queue (SQS / Pub-Sub / Service Bus) via **LocalStack** | Real durability, DLQ behavior, delivery SLAs, scaling limits |
| **2 — Registry / routing** | Registry + selector + mock provider services — all local | — | Service discovery at real scale |
| **3 — Rate limit / breaker / retry ⭐** | Shared counters + breaker state in local Redis; full resilience logic | — | Behavior under real network latency/jitter across nodes |
| **4 — Multi-tenancy / auth / networking** | API-key auth, quotas, ledger; **Vault** (already in repo) ≈ Secrets Manager | IAM (LocalStack, toy); VPC/subnets/SG/NACL/PrivateLink (k8s NetworkPolicies ≈ isolation *concept*) | Real IAM policy evaluation, true L3 network isolation, PrivateLink |
| **5 — CQRS / compaction / archival / migration** | Read model, snapshots, compaction job; archive to **MinIO** or LocalStack-S3; expand-contract migration | S3 lifecycle/tiering rules (LocalStack approximates) | Real object-storage tiering, lifecycle policies, durability guarantees |
| **6 — Platform / observability / DR** | **minikube** + **Helm** + Argo CD; Prometheus/Grafana/Loki/Tempo/OTel; HPA on a custom (queue-depth) metric; graceful drain | Multi-AZ / multi-region & static stability (multiple kind clusters — clunky) | True zone-loss failover, managed control plane, autoscaling under real load, p99 at scale |
| **Wk 8 — Cost / Well-Architected** | Cost **model** via the pricing calculator; WAF self-review; ADRs; diagrams | — | A real bill (which you *want* to avoid — modeling is free) |

**The one paid touch worth it:** in Week 7, deploy Helios *once* to real **EKS/ECS + RDS + SQS inside a VPC with IAM** (AWS free tier + ~$20–50 credits). It turns "I designed it" into "I designed it locally and deployed it on AWS," makes VPC/IAM/managed-service tradeoffs concrete, and directly reinforces SAA-C03. Tear it down after.

---

## 9. Local environment setup checklist

> Install **just-in-time** — don't set up 12 tools on day one. The first 5 weeks need only a container runtime + Compose.

### Run in tiers (16 GB RAM is the real constraint — never run all at once)
| Tier | What's up | Approx RAM | Use it for |
|---|---|---|---|
| **A** | Compose: app + Postgres + Redis + a few workers | ~2–4 GB | Daily dev — all of Phases 0–5 |
| **B** | Local k8s (minikube/kind) + Helm + Argo CD | ~4–8 GB | Practicing k8s / GitOps (Phase 2+, Phase 6) |
| **C** | Tier B **+** full observability (Prometheus/Grafana/Loki/Tempo/OTel) | ~12–14 GB | Week 7 only — run the session, then **tear down** |

For Tier C: trim Prometheus retention + scrape interval, give minikube a bounded memory cap, and close Chrome/other RAM hogs. Don't keep it running 24/7.

### Tooling — present vs install
| Tool | Purpose | Status on this Mac |
|---|---|---|
| **Colima** (recommended) | Container runtime, lighter than Docker Desktop on 16 GB | install (`brew install colima docker`) |
| Docker Desktop / Rancher Desktop | Alternative runtimes | optional alternatives to Colima |
| **minikube** | Local Kubernetes | ✅ present |
| **Helm** | K8s packaging (your charts) | ✅ present |
| **kubectl** | K8s CLI | verify / install if missing |
| Docker Compose | Tier-A local stack | ✅ present |
| **Terraform** | IaC (Week 7) | install when you reach IaC |
| **LocalStack** | Fake AWS APIs (S3/SQS/IAM) locally | install when simulating cloud (Phase 1/5) |
| **MinIO** | Local S3-compatible object store (archival) | install at Phase 5 (or use LocalStack-S3) |
| **awscli** | Talk to LocalStack and (Week 7) real AWS | install at Phase 5 / Week 7 |
| **Locust** | Load testing | ✅ already used in repo |
| k9s (optional) | TUI for inspecting the cluster | quality-of-life, optional |

### Install order by week
- **Weeks 1–2:** container runtime (Colima) only → run Tier A. (Verify the Docker daemon is actually up — right now it isn't.)
- **Week 3:** optionally bring up minikube (Tier B) to deploy the registry service via Helm.
- **Weeks 4–5:** still mostly Tier A; add LocalStack when you want to simulate a managed queue/secrets.
- **Week 6:** MinIO/LocalStack-S3 for archival; Terraform if you start codifying infra.
- **Week 7:** full Tier C (observability) + awscli + Terraform; optional real AWS deploy.

### First action before Week 1
Your Docker daemon is **not running** right now. Start your container runtime (Colima or Docker Desktop) and confirm a container can launch — that's the only blocker between you and Tier A.
