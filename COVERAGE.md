# Coverage Analysis — what this project does (and doesn't) cover

> **Caveat 1:** This maps the project against the **Emergent candidate *interview prep guide*** (the MC/HLD/LLD rounds + "What Emergent Values") — that's an evaluation rubric, **not a job description**. For a precise requirement-by-requirement check, paste the actual JD and this file will be updated into a JD-coverage table.
>
> **Caveat 2:** All percentages are **depth estimates** — "how far this project takes you toward production/architect-level proficiency in that technology," *not* precise metrics and *not* resume claims. Use them to spot strengths vs. gaps.

---

## 1. Coverage vs the interview guide

| Evaluated area | Covered? | How |
|---|---|---|
| Machine Coding (concurrency, rate limiting, state machines, retry/fallback) | ✅ Strong | Phase 3 is built around exactly these |
| HLD (decomposition, queues, failure domains, scale reasoning) | ✅ Strong | Phases 1–6 + the Exceptional-4 diagram |
| LLD (schemas, OCC, idempotency, event sourcing, migration, compaction) | ✅ Strong | Phases 0, 1, 5 |
| Production thinking / "what breaks at 3am" | ✅ Strong | Failure playbook, DR, observability |
| Tradeoff reasoning & communication | ✅ Strong | ADRs, service-selection table, WAF review |
| Ownership / on-call instinct | ✅ Strong | Existing SRE stack + runbooks |

**Interview-round coverage: ~85–90%** (the project was designed around these rounds).

---

## 2. Technology coverage (% depth at the FULL master-program target)

> Updated 2026-06-30 for the 6–12 month master program (`MASTER-BUILD-PROGRAM.md`). "Stage" = stage in that
> program. These are *target depths at completion*, not the old 8-week sprint numbers.

### Programming & API & agents
| Tech | % | Stage |
|---|---|---|
| Python (FastAPI, async, backend) | 75 | all |
| Go (goroutines, channels, context) | 60 | Stage 7 |
| Async / concurrency (asyncio, locks, semaphores) | 75 | Stage 1, 3 |
| REST + gRPC + GraphQL API design (idempotency, versioning) | 80 | Stage 0–7 |
| Agent / LLM orchestration (loops, tool use, token budgeting, multi-agent, eval) | 80 | Stage 3 |

### Data & storage
| Tech | % | Phase |
|---|---|---|
| PostgreSQL (indexing, OCC, partitioning, migration) | 80 | 0, 1, 5 |
| Redis (atomic ops, Streams, caching) | 75 | 1, 3 |
| Event sourcing / CQRS | 70 | 1, 5 |
| Object storage (S3 / MinIO, lifecycle) | 55 | Stage 2, 11 |
| MongoDB / document DB (modeling, aggregation, change streams) | 75 | Stage 2 |
| Vector DB / RAG (pgvector / Qdrant, embeddings) | 65 | Stage 3 |
| OLAP / warehouse + CDC (ClickHouse/DuckDB, Debezium) | 55 | Stage 5 |

### Messaging
| Tech | % | Phase |
|---|---|---|
| Queues (Redis Streams) | 70 | Stage 1 |
| Kafka / Redpanda (partitions, consumer groups, replay, exactly-once) | 70 | Stage 5 |
| Schema registry + evolution, Saga, outbox, DLQ | 65 | Stage 5 |
| SQS / MSK | 45 | Stage 11 |

### Distributed systems & resilience
| Tech | % | Phase |
|---|---|---|
| Rate limiting / circuit breaker / retry / fallback / load shedding | 85 | 3 |
| State machines | 85 | 1 |
| Idempotency / delivery semantics | 80 | Stage 1 |
| Consensus (Raft/etcd), leader election, consistent hashing | 60 | Stage 5, 8 |

### Containers / orchestration / delivery
| Tech | % | Phase |
|---|---|---|
| Docker (multi-stage, distroless, scanning) | 85 | all |
| Kubernetes deep (RBAC, NetworkPolicies, PodSecurity, StatefulSets) | 80 | Stage 8 |
| Custom Operator + CRD, KEDA, admission control (Kyverno/OPA) | 65 | Stage 8 |
| Helm + Kustomize | 80 | Stage 8 |
| GitHub Actions CI (OIDC to cloud, reusable workflows) | 75 | existing + Stage 8 |
| ArgoCD / GitOps + Argo Rollouts (canary/blue-green) | 75 | existing + Stage 8 |
| Service mesh (Istio / Linkerd, mTLS) | 60 | Stage 7 |
| gRPC + Protobuf | 65 | Stage 7 |
| Supply-chain security (SBOM, cosign, SLSA) | 55 | Stage 12 |

### IaC / cloud / networking
| Tech | % | Phase |
|---|---|---|
| Terraform (modules, remote state, Terratest) + Crossplane | 75 | Stage 11 |
| Ansible | 50 | existing |
| AWS core (VPC, EKS/IRSA, RDS, MSK, S3, KMS, ALB, Route53, CloudFront, WAF) | 70 (→80 with SAA-C03) | Stage 11 |
| GKE + Cloudflare (R2/Workers) — multi-cloud literacy | 45 | Stage 11 |
| Networking (VPC, SG/NACL, PrivateLink, Route53, ingress, mesh) | 70 | Stage 7, 11 |
| Multi-region / DR (active-passive → active-active) | 60 | Stage 11 |

### Observability / security / testing / architecture
| Tech | % | Phase |
|---|---|---|
| Prometheus / Grafana (recording rules, Alertmanager) | 85 | existing + Stage 12 |
| Loki / logging | 75 | existing |
| OpenTelemetry / distributed tracing (Tempo/Jaeger) | 75 | Stage 12 |
| Continuous profiling (Pyroscope) + optional eBPF | 50 | Stage 12 |
| SLO / SLI / error budgets + burn-rate alerts | 75 | Stage 12 |
| Vault deep (dynamic secrets, PKI) / External Secrets | 75 | Stage 6 |
| Auth + real IdP (Keycloak/Cognito, OAuth2/OIDC/JWT) | 70 | Stage 6 |
| IAM / least privilege (incl. IRSA) | 65 | Stage 11 |
| Chaos engineering (Chaos Mesh) | 60 | Stage 12 |
| Load testing (k6 / Locust), capacity planning | 70 | Stage 12 |
| Experimentation / A-B framework (flags, traffic split, significance) | 65 | Stage 9 |
| Frontend (React / Next.js / TypeScript, SSE) | 65 | Stage 9 |
| Preview-environment platform (vcluster, cert-manager, external-dns) | 60 | Stage 10 |
| Diagrams (C4) / ADRs / WAF review / cost modeling (FinOps) | 75 | Stage 12 |

---

## 3. Former gaps — NOW CLOSED by the full program

> Scope changed (2026-06-30): no fixed deadline, 6–12 months, "build the flagship / learn everything."
> The maximal program in **`MASTER-BUILD-PROGRAM.md`** folds every former gap in as a first-class stage.
> Percentages below are the program's *target depth*, not the old 8-week sprint.

| Former gap | Now covered in | New target depth |
|---|---|---|
| Frontend (React/Next.js/TypeScript) | Stage 9 (dashboard + live trajectory via SSE) | 65% |
| MongoDB / document modeling | Stage 2 (polyglot persistence) | 75% |
| Agent / LLM frameworks (real loops, RAG, trajectories) | Stage 3 | 80% |
| Compiled language (Go) | Stage 7 (rewrite a service in Go) | 60% |
| Kafka / streaming at scale | Stage 5 (Kafka/Redpanda backbone) | 70% |
| Multi-region | Stage 11 (active-passive → active-active) | 60% |
| Deep cloud networking & IAM | Stage 11 (real Terraform VPC/EKS/IRSA) | 70% |

Plus net-new at full scope: gRPC, service mesh (Istio), custom k8s Operator/CRD, KEDA, CDC (Debezium),
Saga, vector DB/RAG, real IdP (Keycloak/OIDC), Vault dynamic secrets, supply-chain security
(SBOM/cosign/SLSA), chaos engineering, continuous profiling, the experimentation/A-B framework, and the
per-tenant preview-environment platform — i.e. **all three Emergent flagship design problems**.

---

## 4. Bottom line (full program)

| If the JD is for… | Project coverage |
|---|---|
| Platform / Backend / SRE / DevOps-leaning **Cloud Architect** | **~90–95%** of the technical bar |
| Full-stack or agent-product engineering | **~80–85%** (frontend + real agent loops now included) |
| Emergent-shaped platform engineering | **High** — mirrors their stack (Mongo, GKE, agents, preview envs) and builds all 3 flagship designs |

The remaining deltas are mostly *real-world operational scale* (true production traffic, years-long
data growth, large-team process) that no solo project fully reproduces — you reason about those via
the Well-Architected review and scale-at-100x analysis (Stage 12).

**Still worth doing when available:** paste the real JD → convert this into a precise
requirements-by-requirement coverage table.
