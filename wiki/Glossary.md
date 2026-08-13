# Glossary

Key terms used across Cosmos. Fuller explanations (with diagrams) live in the [[Deliverables and Study Material|Learning Notes]].

**202 + id** — the accept-fast pattern: the gateway validates and returns `202 Accepted` + a job id in milliseconds, then processes the work asynchronously. The id is the client's claim ticket (poll or stream for the result).

**Idempotency** — the same request applied twice has the same effect as once. Essential for safe retries; usually keyed by a client-supplied idempotency key.

**Optimistic concurrency (OCC)** — detect conflicting concurrent writes via a version check instead of locking; the loser retries.

**Event sourcing** — persist every state change as an appended, immutable event; current state is a projection of the log, and history is replayable.

**CQRS** — Command Query Responsibility Segregation: separate the write model from purpose-built read models (often fed by the event log).

**Saga** — a long-running, multi-step transaction coordinated as a series of local steps with compensating actions on failure (orchestration or choreography).

**Outbox pattern** — write domain changes and their outgoing events in one DB transaction; a relay publishes the events, guaranteeing "state changed ⇔ event sent."

**CDC (Change Data Capture)** — stream a database's changes (e.g. via Debezium) into other systems, such as Postgres → warehouse.

**Idempotent consumer** — a message consumer that safely tolerates at-least-once delivery (duplicates cause no double effects).

**Agent loop** — plan → act (tool call) → observe → iterate, bounded by a token budget; the run's full trace is the **trajectory**.

**RAG** — Retrieval-Augmented Generation: retrieve relevant context (via embeddings + vector search) and feed it to the model.

**Token budget** — a hard ceiling on tokens spent per job, so an agent loop can't run away in cost.

**Circuit breaker** — after repeated failures a breaker "opens" to stop calling a failing dependency, "half-opens" to test recovery, then "closes".

**Retry with backoff + jitter** — retry failed calls with exponentially increasing, randomized delays to avoid synchronized retry storms.

**Load shedding** — deliberately reject excess work under overload to protect the system's core throughput.

**Rate limiter (token bucket / sliding window)** — cap request rate per tenant/provider; distributed via Redis/Lua so it holds across replicas.

**SLI / SLO / error budget** — SLI = a user-centric reliability measurement; SLO = its target; error budget = `100% − SLO`, the allowed unreliability that gates how much risk you ship.

**Burn-rate alerting** — page on how fast the error budget is being consumed (multi-window), not on every raw error.

**KEDA** — Kubernetes event-driven autoscaling; here, scaling workers on Kafka consumer lag / queue depth.

**Operator / CRD** — a custom Kubernetes controller (Operator) that reconciles a custom resource (CRD) — e.g. an `AgentJob` or `CosmosTenant`.

**IRSA** — IAM Roles for Service Accounts: give each k8s pod its own short-lived, scoped AWS credentials via OIDC — no static keys.

**vcluster** — a virtual Kubernetes cluster (own API server) running inside a host namespace; stronger isolation than a plain namespace.

**SLSA / SBOM / cosign** — supply-chain security: build **provenance** (SLSA), a software **bill of materials** (SBOM), and artifact **signing/verification** (cosign/sigstore).

**Well-Architected** — AWS's 6-pillar review framework (Operational Excellence, Security, Reliability, Performance, Cost, Sustainability).

**ADR** — Architecture Decision Record: a short doc capturing one decision, its context, and trade-offs. Cosmos targets 30+.
