# Target Architecture

The **maximal** architecture Cosmos grows into, described in planes. (You draw the C4 versions yourself; the interactive version is in the deliverables.)

## Request path, end to end

```
Client → Cloudflare/CDN → WAF → API Gateway (FastAPI) → Kafka backbone
      → Go worker fleet (agent loops: Claude + tools + RAG) → LLM providers
      ↑ resilience wraps every provider call (rate-limit · breaker · retry/fallback · load-shed)
      ↕ gRPC for internal sync calls · Istio service mesh for mTLS + traffic shaping
results & events → polyglot storage → CQRS read models → dashboard (SSE live trajectory)
```

## The planes

| Plane | What lives here |
|---|---|
| **Edge / ingress** | Cloudflare/CDN → WAF → API Gateway → ingress controller (TLS via cert-manager/ACM) |
| **Frontend** | Next.js/React dashboard + ops console; live trajectory via SSE/WebSocket |
| **Control plane** | Provider registry · tenant/quota admin · feature-flag & experimentation service · **preview-environment provisioner (custom k8s Operator)** · identity (Keycloak/Cognito) |
| **Data plane (request path)** | API gateway (FastAPI) → **Kafka** → **Go worker fleet** running agent loops → providers; resilience wrapping real LLM calls; gRPC internal; Istio mesh |
| **Storage plane (polyglot)** | Postgres (jobs/tenants/quota/ledger) · MongoDB (trajectories/payloads) · Redis (hot state/cache) · vector DB (RAG embeddings) · object storage (archive) · warehouse (analytics / CQRS read) |
| **Platform plane** | Kubernetes (multi-region EKS + a GKE touch) · Argo CD/Rollouts (GitOps + canary) · KEDA autoscaling on Kafka lag · Terraform/Crossplane · Vault |
| **Observability plane** | OTel traces + Prometheus metrics + Loki logs + Grafana + Pyroscope profiling · SLOs · chaos experiments |

## Component map (from the interactive diagram)

Client & Edge · Presentation · API Gateway · Control plane · **Resilience layer** · **Event backbone** · **Worker fleet · Go** · LLM providers · **Storage plane · polyglot** · Platform & runtime · Delivery & supply chain · Observability & SRE.

## Key design commitments

- **Accept fast, process later** — the gateway returns `202 + job id` in milliseconds; work happens asynchronously on the worker fleet.
- **Event-sourced** — every state change is an appended event; state is a projection, history is replayable.
- **Resilient by construction** — rate-limit, circuit-breaker, retry-with-jitter, and fallback wrap every provider call; load-shedding protects the system under overload.
- **Polyglot persistence** — the right datastore per data shape, not one database stretched over everything.
- **Multi-tenant & isolated** — quotas, usage ledger, fair scheduling, and shuffle-sharding-style isolation.

## See it rendered

- **Interactive architecture** (Flow + 3-D stack, clickable component cards): [`docs/architecture.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/architecture.html) · PDF: [`docs/Cosmos-Architecture.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Architecture.pdf)
- The **[[Current Platform]]** page shows the subset that is already built and running.

→ Next: **[[The 12 Stage Build]]** · **[[Technology Catalog]]**
