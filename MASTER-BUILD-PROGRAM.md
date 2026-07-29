# Nataraja — The Complete Build Program (6–12 months, "learn everything")

> **This is now the master spine.** No time pressure: the goal is maximal, coherent complexity — a production-grade, multi-cloud, agentic platform that exercises every layer a Cloud Solution Architect owns. You write **100% of the code**; this doc is the map, the full technology catalog, the staged build, and what to refer for each piece. **No code here.**
>
> **Doc map:** this file = the overarching program. `CLOUD-ARCHITECT-PLAN.md` = the reference library + CSA framing (still valid). `SCALING-ROADMAP.md` = detailed acceptance criteria for the early phases (a subset of Stage 0–6 here). `COVERAGE.md` = what's covered + gaps. Read this file first.

---

## 0. The vision — what Nataraja becomes at full scope

A multi-tenant, event-driven **agent-orchestration platform**: users submit goals; the platform runs autonomous LLM agents (plan → act → observe loops with tool use and RAG) on a worker fleet, routed across providers under rate-limit + health constraints, with every trajectory persisted, billed, observable, and A/B-testable — deployed across regions on real cloud infra, with a self-service frontend and per-tenant preview environments.

That single system legitimately requires: 3+ languages, polyglot persistence (5 datastore types), an event-streaming backbone, service mesh, a custom Kubernetes operator, multi-region cloud infra, real identity, supply-chain security, full observability, chaos engineering, an experimentation framework, and a frontend. That's the point — it's the vehicle to learn all of it.

### It covers all three Emergent flagship design problems
1. **Agent orchestration platform** → the core of Nataraja (Stages 1–8).
2. **Experimentation / A-B framework for agent configs** → Stage 9.
3. **Deployment pipeline with per-user preview environments** → Stage 10.

---

## 1. The complete technology & concept catalog (what "everything" means)

Sixteen tracks. Each is woven through the staged build (Section 3). This is your "what will we cover" answer.

| # | Track | Technologies / concepts |
|---|---|---|
| **T1** | **Languages & service comms** | Python (FastAPI, async), **Go** (goroutines/channels/context), optionally **Rust or Java** for one component; **gRPC + Protobuf**, REST, **GraphQL** (BFF); OpenAPI, contract testing |
| **T2** | **Agent / LLM layer** | Agentic loops (plan-act-observe), **tool/function calling**, multi-agent patterns (orchestrator-worker, evaluator-optimizer, routing), prompt & **context-window management**, **token budgeting**, trajectory storage & replay, **RAG** (embeddings, vector search), streaming (SSE), eval harnesses, prompt-injection defense, LLM cost control |
| **T3** | **Data & storage (polyglot)** | **PostgreSQL** (indexing, partitioning, replication, query plans), **MongoDB** (document modeling, aggregation, change streams, TTL), **Redis** (cache, Streams, pub/sub, Lua), **vector DB** (pgvector / Qdrant), **object storage** (S3/MinIO), **OLAP/warehouse** (ClickHouse / DuckDB / BigQuery), **CDC** (Debezium), connection pooling (PgBouncer) |
| **T4** | **Messaging & event-driven** | **Kafka / Redpanda** (partitions, consumer groups, offsets, replay, exactly-once), **schema registry** + schema evolution, **event sourcing + CQRS**, **Saga** (orchestration & choreography), **outbox pattern**, DLQ, stream processing (Kafka Streams / Flink concepts) |
| **T5** | **Distributed systems** | **Consensus (Raft / etcd)**, distributed locking & **leader election**, **consistent hashing**, quorums, replication strategies, vector clocks & ordering, **CAP/PACELC** in practice, distributed rate limiting |
| **T6** | **Resilience & reliability** | Circuit breaker, bulkhead, retry/backoff/jitter, rate limiting, **load shedding**, graceful degradation, backpressure, **chaos engineering** (Chaos Mesh/Litmus), fault injection |
| **T7** | **Containers & orchestration** | Docker (multi-stage, distroless, scanning), **Kubernetes deep** (RBAC, NetworkPolicies, PodSecurity, StatefulSets), **custom Operator + CRDs**, **KEDA** (event-driven autoscale), HPA/VPA, admission control (**Kyverno / OPA Gatekeeper**), Helm + **Kustomize**, multi-cluster |
| **T8** | **CI/CD, GitOps, progressive delivery** | GitHub Actions (reusable workflows, **OIDC to cloud**), **Argo CD + Argo Rollouts** (canary/blue-green/analysis), Argo Workflows/Tekton, **feature flags**, **supply-chain security** (SBOM, **cosign/sigstore** signing, **SLSA** provenance), policy-as-code |
| **T9** | **Infrastructure as Code** | **Terraform deep** (modules, remote state, Terragrunt, **Terratest**), **Pulumi** (optional), **Crossplane** (k8s-native infra), Ansible |
| **T10** | **Cloud (multi-cloud architect)** | **AWS** (VPC, IAM/**IRSA**, EKS, RDS, ElastiCache, MSK/SQS, S3, Secrets Manager, ALB/NLB, Route53, CloudFront, ACM, WAF, KMS); **multi-AZ → multi-region** (active-passive → active-active); **GKE** touch (multi-cloud, Emergent-relevant); **Cloudflare** (R2, Workers); **FinOps** (Infracost, budgets, tagging); landing zone; Well-Architected (6 pillars) |
| **T11** | **Networking** | VPC/subnets/route tables/NAT/IGW, **SG vs NACL**, **PrivateLink / VPC endpoints**, peering/Transit Gateway, **DNS** (Route53), L4/L7 LB, **ingress controllers**, **cert-manager / ACM / mTLS**, **API gateway** (Kong/AWS API GW), service-mesh networking, zero-trust |
| **T12** | **Security & identity** | IAM least-privilege, RBAC, **OAuth2/OIDC/JWT** with a real IdP (**Keycloak / Cognito**), **Vault deep** (dynamic secrets, PKI), External Secrets, encryption (KMS, envelope, in-transit/at-rest), OWASP + API security, supply-chain security, secret scanning, SAST/DAST, compliance (SOC2/data residency concepts) |
| **T13** | **Service mesh** | **Istio / Linkerd** — mTLS, traffic shaping, retries/timeouts at mesh layer, observability, canary via mesh |
| **T14** | **Observability & SRE** | **Prometheus** (recording rules, Alertmanager), **OpenTelemetry** + **Tempo/Jaeger** tracing, **Loki/ELK** logs, **Grafana**, **continuous profiling (Pyroscope)**, optional **eBPF (Cilium/Pixie)**, **SLO/SLI/error budgets + burn-rate alerts**, runbooks, postmortems, on-call (PagerDuty) |
| **T15** | **Scalability, performance, data-eng** | Load testing (**k6/Locust/Gatling**), capacity planning & queueing theory, multi-layer caching + invalidation, **read replicas / sharding**, tail-latency optimization, **analytics pipeline** (events→warehouse), **experimentation/A-B framework** (traffic splitting, significance, guardrails) |
| **T16** | **Architecture & communication** | **C4 diagrams**, **ADRs**, design docs/RFCs, **Well-Architected reviews**, cost models, **DR runbooks**, failure playbooks, scale-at-100x analysis, stakeholder communication |

---

## 2. Target architecture (maximal — what you grow into)

Described in planes; you'll draw the C4 versions yourself.

- **Edge / ingress:** Cloudflare/CDN → WAF → API Gateway → ingress controller (TLS via cert-manager/ACM).
- **Frontend plane:** Next.js/React dashboard + ops console (live trajectory via SSE/WebSocket).
- **Control plane:** provider registry, tenant/quota admin, **feature-flag/experimentation** service, **preview-environment provisioner** (custom k8s Operator), identity (Keycloak/Cognito).
- **Data plane (request path):** API gateway (FastAPI) → **Kafka** backbone → **Go worker fleet** running **agent loops** (Claude + tools + RAG) → providers; resilience (rate limit, breaker, retry/fallback) wrapping real LLM calls; **gRPC** for internal sync calls; **service mesh (Istio)** for mTLS + traffic shaping.
- **Storage plane (polyglot):** Postgres (jobs/tenants/quota/ledger), MongoDB (trajectories/payloads), Redis (hot state/cache), vector DB (RAG embeddings), object storage (archive), warehouse (analytics/CQRS read).
- **Platform plane:** Kubernetes (multi-region EKS + a GKE touch), Argo CD/Rollouts (GitOps + canary), KEDA autoscaling on Kafka lag, Terraform/Crossplane infra, Vault.
- **Observability plane:** OTel traces + Prometheus metrics + Loki logs + Grafana + Pyroscope, SLOs, chaos experiments.

---

## 3. The staged build program (12 stages)

> Each stage = a working increment + a concept cluster + what to refer. Sequence matters — each builds on the last. Pace it over 6 months (aggressive) or 12 (thorough). **Don't start a stage until the previous one's increment runs.**

### Stage 0 — Foundations & clean architecture
- **Build:** rewrite to **FastAPI** (async-native), hexagonal layering (ports/adapters), validation, consistent errors, correlation IDs, idempotency, optimistic concurrency, 12-factor config.
- **Tracks:** T1, T16. **Refer:** *Fundamentals of Software Architecture*; 12factor.net; FastAPI docs; Cloud Design Patterns (*Idempotency*, *Health Endpoint Monitoring*).

### Stage 1 — Async core: jobs, queue, state machine, event sourcing
- **Build:** job submission (202), durable queue (start with Redis Streams), worker, explicit job **state machine**, append-only **event log**, at-least-once + idempotent consumer, cancellation.
- **Tracks:** T4, T5, T3. **Refer:** DDIA Ch.1,5,9; Cloud Design Patterns (*Queue-Based Load Leveling*, *Competing Consumers*, *Event Sourcing*, *CQRS*); Fowler *Event Sourcing*.

### Stage 2 — Polyglot persistence: MongoDB + the data layer
- **Build:** keep relational core in Postgres; move trajectories/payloads/results to **MongoDB**; Redis for hot state. Write the **"why polyglot persistence" ADR**. Mongo modeling (embed vs reference), aggregation pipeline, **change streams**, TTL indexes.
- **Tracks:** T3. **Refer:** DDIA Ch.2; MongoDB *Data Modeling* docs + "6 Rules of Thumb for Schema Design"; MongoDB University M001 + M320.

### Stage 3 — The agent layer: real LLM orchestration + RAG
- **Build:** a job type that runs a real **agent loop** with **Claude (Anthropic API)** — plan → tool-call → observe → iterate, bounded by a **token budget**; persist the full **trajectory** to Mongo; **stream** output via SSE. Add **multi-agent patterns** (orchestrator-worker, evaluator-optimizer). Add **RAG**: embeddings + **vector DB** (pgvector or Qdrant) + semantic retrieval. Build a small **eval harness**.
- **Tracks:** T2, T3 (vector). **Refer:** Anthropic API docs (Messages, **tool use**); Anthropic **"Building Effective Agents"** guide; the interview guide's chat-storage/token-budget LLD prompt. *(In a Claude Code session, invoke the `claude-api` skill for exact API details.)*
- **Note:** this is the Emergent core. Costs a small Anthropic spend. Your Stage-4 resilience will wrap these real calls.

### Stage 4 — Routing, registry & resilience (gateway hardening) ⭐
- **Build:** runtime **provider registry**; **selector** strategies (round-robin/weighted/least-loaded); **rate limiter** (token bucket + sliding window, distributed via Redis/Lua); **circuit breaker** (closed/open/half-open); **retry + backoff + jitter**; **fallback chain**; **load shedding** — all wrapping the real providers from Stage 3.
- **Tracks:** T6, T5. **Refer:** *Release It!* (stability patterns); **Amazon Builders' Library** (*Timeouts/retries/backoff with jitter*, *Load shedding*, *Avoiding fallback*); Cloud Design Patterns (*Retry*, *Circuit Breaker*, *Throttling*, *Bulkhead*).

### Stage 5 — Event-driven backbone: Kafka + CQRS + Saga + CDC
- **Build:** introduce **Kafka (Redpanda locally)** as the backbone; partitions, consumer groups, replay, **exactly-once**, DLQ; **schema registry** + schema evolution; **outbox pattern**; **CQRS** read models; **Saga** for multi-step jobs; **CDC (Debezium)** to stream Postgres→warehouse.
- **Tracks:** T4, T3, T15. **Refer:** DDIA Ch.11 (stream processing); Kafka docs + Confluent "Kafka 101"; Redpanda docs; microservices.io (*Saga*, *Transactional Outbox*); Debezium docs.

### Stage 6 — Multi-tenancy, identity & security
- **Build:** tenants, **API keys**, quotas, **usage ledger**, fair scheduling; a real IdP (**Keycloak** or Cognito) with **OAuth2/OIDC/JWT**; **Vault deep** (dynamic DB creds, PKI); RBAC; encryption in transit/at rest; **prompt-injection defenses** on the agent layer.
- **Tracks:** T12, T5 (shuffle-sharding isolation). **Refer:** Well-Architected Security pillar; OAuth/OIDC specs; Keycloak docs; Vault docs (dynamic secrets, PKI); OWASP Top 10 + API Security Top 10; Amazon Builders' Library *"Workload isolation using shuffle-sharding."*

### Stage 7 — Internal comms: gRPC, service mesh, polyglot Go
- **Build:** **gRPC + Protobuf** between internal services; **rewrite the worker (or rate-limiter) in Go** (goroutines, channels, `context`, `x/time/rate`); deploy a **service mesh (Istio/Linkerd)** for mTLS + traffic shaping. Now polyglot microservices.
- **Tracks:** T1, T13, T11. **Refer:** "A Tour of Go" + "Effective Go" + "Go by Example"; Rob Pike's Go concurrency talks; gRPC docs + Protobuf guide; Istio/Linkerd docs. ADR: "why Go for the worker," "why gRPC internally."

### Stage 8 — Kubernetes deep + custom Operator + event-driven autoscaling
- **Build:** production k8s (RBAC, NetworkPolicies, PodSecurity, PDB); **KEDA** autoscaling on **Kafka consumer lag / queue depth**; **build a custom Operator + CRD** (e.g. an `AgentJob` or `NatarajaTenant` CRD); admission control (**Kyverno/OPA**); StatefulSets/operators for the data stores; **Kustomize** overlays.
- **Tracks:** T7. **Refer:** Kubernetes docs (CRDs, controllers); **Kubebuilder** / Operator SDK book; KEDA docs; Kyverno/OPA Gatekeeper docs; *Programming Kubernetes* (O'Reilly).

### Stage 9 — Frontend + experimentation/A-B framework
- **Build:** a **Next.js/React/TypeScript** dashboard — submit jobs, **live trajectory view** (SSE/WebSocket), queue/health/usage/breaker dashboards, ops console. Build the **experimentation framework** (Emergent flagship #3): **feature flags**, **traffic splitting** across agent configs/models, metric collection, **statistical significance**, guardrails/auto-rollback.
- **Tracks:** T15, T1 (frontend). **Refer:** Next.js docs/tutorial; react.dev "Learn"; TypeScript handbook; experimentation reading (Microsoft/Optimizely A-B testing guides; "Trustworthy Online Controlled Experiments" — Kohavi, for depth).

### Stage 10 — Deployment pipeline + per-tenant preview environments
- **Build:** the Emergent flagship #2 — **ephemeral per-tenant preview environments**: provision isolated stacks on demand (namespace-per-tenant or **vcluster**), wire **domains + TLS** (external-dns + cert-manager), lifecycle/teardown, GitOps-driven. Your Stage-8 Operator powers this.
- **Tracks:** T7, T8, T11, T9. **Refer:** vcluster docs; external-dns + cert-manager docs; Argo CD ApplicationSets; the interview guide's preview-environment prompt.

### Stage 11 — Cloud, networking, IaC, multi-region (the real deploy)
- **Build:** **Terraform** a real AWS env — **VPC** (multi-AZ public/private subnets), **EKS w/ IRSA**, **RDS**, **ElastiCache**, **MSK**, **S3**, **Secrets Manager**, **ALB**, **Route53**, **CloudFront**, **ACM**, **WAF**, **KMS**. Then **multi-region** (active-passive → active-active) with data replication + failover. A **GKE** deploy for multi-cloud literacy; **Cloudflare R2/Workers** touch. **FinOps:** Infracost in CI, budgets, tagging, cost allocation. **Crossplane** as a k8s-native IaC alternative (optional).
- **Tracks:** T10, T11, T9. **Refer:** AWS VPC + IAM best-practices docs; AWS EKS Workshop (IRSA/VPC labs); Terraform AWS module docs + Terratest; Well-Architected Reliability + Cost pillars; *Cloud FinOps*.

### Stage 12 — Observability, SRE, chaos, supply-chain, capstone
- **Build:** full o11y — **OTel** traces + **Prometheus** metrics (+ recording rules/Alertmanager) + **Loki** logs + **Grafana** + **Pyroscope** profiling (+ optional **eBPF/Cilium**); **SLOs + burn-rate alerts**; runbooks; **chaos engineering (Chaos Mesh)**; **supply-chain security** (SBOM, **cosign** signing, **SLSA** provenance) in CI; **load testing (k6)** at scale. Then the **capstone artifacts:** Well-Architected review (6 pillars), cost model, the Exceptional-4 diagram, failure playbook, scale-at-100x.
- **Tracks:** T14, T6, T8, T15, T16. **Refer:** Google **SRE Book** + **SRE Workbook**; OpenTelemetry docs; Chaos Mesh docs; sigstore/cosign + SLSA docs; k6 docs.

---

## 4. Pacing & how not to drown

- **6-month track (aggressive, ~20 hrs/wk):** ~2 weeks/stage. Skip the "optional" extremes (Rust, Pulumi, eBPF, GKE multi-cloud).
- **12-month track (thorough, ~10 hrs/wk):** ~4 weeks/stage. Include the extremes; go deep on each ADR and reference.
- **Rules to stay sane:**
  1. **One stage at a time** — each must produce a *running* increment before you move on. A half-built stage you abandon teaches nothing.
  2. **Read before you build** (each stage's "refer" list is a prerequisite).
  3. **Write an ADR per real decision** as you go — by the end you have 30+ ADRs, the strongest possible interview asset.
  4. **Tear down heavy stacks** when not in use (16 GB laptop) — see `CLOUD-ARCHITECT-PLAN.md` §9 tiers. The cloud (Stage 11) relieves the RAM ceiling.
  5. **Keep a running architecture diagram** — redraw it after every stage.
- **Don't let scope hide the fundamentals:** the *patterns* (Stages 1–6) matter more than the *tech count*. A perfect circuit breaker beats a half-working service mesh in any interview.

---

## 5. Definition of done (the flagship portfolio)

When complete you have, in one repo + cloud account:
- A running multi-region, multi-cloud, agentic platform spanning 3 languages and 5+ datastore types.
- All three Emergent flagship designs built (agent orchestration, experimentation, preview environments).
- **30+ ADRs**, a Well-Architected review, a cost model, DR runbooks, a failure playbook, and C4 + Exceptional-4 diagrams.
- A README/design doc that presents the whole system to a stakeholder.
- The ability to whiteboard any layer and defend every tradeoff because you built it.

That is no longer a "DevOps engineer who deployed an app." That is a **Cloud Solution Architect with a system to point at** — and one that mirrors Emergent's own platform end to end.
