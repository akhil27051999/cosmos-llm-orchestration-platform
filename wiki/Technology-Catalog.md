# Technology Catalog

Sixteen tracks — the "what will we cover" answer. Each is woven through the [[The 12 Stage Build]].

| # | Track | Technologies / concepts |
|---|---|---|
| **T1** | Languages & service comms | Python (FastAPI, async), **Go** (goroutines/channels/context), optional Rust/Java; **gRPC + Protobuf**, REST, GraphQL (BFF); OpenAPI, contract testing |
| **T2** | Agent / LLM layer | Agentic loops (plan-act-observe), **tool/function calling**, multi-agent patterns, prompt & **context-window management**, **token budgeting**, trajectory storage/replay, **RAG** (embeddings, vector search), SSE streaming, eval harnesses, prompt-injection defense, cost control |
| **T3** | Data & storage (polyglot) | **PostgreSQL** (indexing, partitioning, replication, query plans), **MongoDB** (modeling, aggregation, change streams, TTL), **Redis** (cache, Streams, pub/sub, Lua), **vector DB** (pgvector/Qdrant), **object storage** (S3/MinIO), **OLAP** (ClickHouse/DuckDB/BigQuery), **CDC** (Debezium), pooling (PgBouncer) |
| **T4** | Messaging & event-driven | **Kafka/Redpanda** (partitions, consumer groups, offsets, replay, exactly-once), **schema registry** + evolution, **event sourcing + CQRS**, **Saga**, **outbox**, DLQ, stream processing |
| **T5** | Distributed systems | **Consensus (Raft/etcd)**, distributed locking & **leader election**, **consistent hashing**, quorums, replication, ordering, **CAP/PACELC**, distributed rate limiting |
| **T6** | Resilience & reliability | Circuit breaker, bulkhead, retry/backoff/jitter, rate limiting, **load shedding**, graceful degradation, backpressure, **chaos engineering**, fault injection |
| **T7** | Containers & orchestration | Docker (multi-stage, distroless, scanning), **Kubernetes deep** (RBAC, NetPol, PSS, StatefulSets), **custom Operator + CRDs**, **KEDA**, HPA/VPA, admission control (Kyverno/OPA), Helm + Kustomize, multi-cluster |
| **T8** | CI/CD, GitOps, progressive delivery | GitHub Actions (reusable workflows, **OIDC to cloud**), **Argo CD + Rollouts** (canary/blue-green/analysis), feature flags, **supply-chain security** (SBOM, **cosign/sigstore**, **SLSA**), policy-as-code |
| **T9** | Infrastructure as Code | **Terraform deep** (modules, remote state, Terragrunt, **Terratest**), Pulumi (optional), Crossplane, Ansible |
| **T10** | Cloud (multi-cloud architect) | **AWS** (VPC, IAM/**IRSA**, EKS, RDS, ElastiCache, MSK/SQS, S3, Secrets Manager, ALB/NLB, Route53, CloudFront, ACM, WAF, KMS); **multi-AZ → multi-region**; GKE touch; Cloudflare (R2, Workers); **FinOps**; Well-Architected (6 pillars) |
| **T11** | Networking | VPC/subnets/route tables/NAT/IGW, **SG vs NACL**, PrivateLink/VPC endpoints, peering/TGW, **DNS** (Route53), L4/L7 LB, ingress controllers, **cert-manager/ACM/mTLS**, API gateway, mesh networking, zero-trust |
| **T12** | Security & identity | IAM least-privilege, RBAC, **OAuth2/OIDC/JWT** with a real IdP (Keycloak/Cognito), **Vault** (dynamic secrets, PKI), External Secrets, encryption (KMS, envelope), OWASP + API security, supply-chain, SAST/DAST |
| **T13** | Service mesh | **Istio/Linkerd** — mTLS, traffic shaping, retries/timeouts at mesh, observability, canary via mesh |
| **T14** | Observability & SRE | **Prometheus** (recording rules, Alertmanager), **OpenTelemetry** + Tempo/Jaeger, **Loki/ELK**, **Grafana**, **continuous profiling (Pyroscope)**, eBPF (optional), **SLO/SLI/error budgets + burn-rate alerts**, runbooks, postmortems, on-call |
| **T15** | Scalability, performance, data-eng | Load testing (**k6/Locust**), capacity planning & queueing theory, multi-layer caching + invalidation, **read replicas/sharding**, tail-latency, analytics pipeline, **experimentation/A-B framework** |
| **T16** | Architecture & communication | **C4 diagrams**, **ADRs**, design docs/RFCs, **Well-Architected reviews**, cost models, **DR runbooks**, failure playbooks, scale-at-100× analysis, stakeholder communication |

→ Next: **[[The 12 Stage Build]]** maps each track onto a stage.
