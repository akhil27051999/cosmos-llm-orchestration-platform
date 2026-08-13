# FAQ

**Q: Can I finish the whole project in 2 months at 5 hrs/day?**
Not the *full* 12 stages at learning depth. 2 months ≈ 8.7 weeks; at 5 hrs/day that's ~217 h (5 days/wk) to ~305 h (7 days/wk), vs the program's ~450–560 h. More importantly, ~60% of the hours are 🔴 *new-skill* stages (0.5, 0, 1, 3, 4, 5) with a learning-absorption floor you can't cram. **What 2 months *does* get you:** own **the spine (Stages 0.5 → 5)** — async core + agent loop + resilience + event backbone — which is exactly where the interview signal is. The leverage back half (7–12) is a fast victory lap afterward. See [[Learning Roadmap]].

**Q: Why scale a CRUD app instead of starting fresh?**
The existing repo already demonstrates strong DevOps/SRE muscle (K8s, GitOps, IaC, observability). Cosmos reuses that as the platform layer and spends new effort only where the genuine gaps are — a faster path to "architect" than rebuilding infra you already know. See [[Current Platform]].

**Q: Why polyglot persistence — isn't one database simpler?**
Different data shapes want different stores: relational integrity (Postgres) for jobs/tenants/ledger, document flexibility (MongoDB) for trajectories/payloads, hot ephemeral state (Redis), similarity search (vector DB), cheap archival (object storage), and analytics (warehouse). The Stage-2 ADR argues the trade explicitly. See [[The 12 Stage Build]] · [[Glossary]].

**Q: Why Go for the worker if the gateway is Python?**
The worker fleet is CPU/concurrency-heavy; Go's goroutines/channels/`context` and `x/time/rate` fit that profile, and being polyglot is itself a learning goal (Stage 7). The gateway stays FastAPI (async I/O-bound). Each choice gets an ADR.

**Q: Does everything need real cloud spend?**
No — ~90% builds and runs locally for free (Docker Compose, minikube/Helm/Argo, LocalStack, local Prometheus/Grafana/Loki). Run in **tiers** and tear heavy stacks down (16 GB laptop). One optional real AWS deploy (~Stage 11) makes it concrete. See [[Current Platform]] and `CLOUD-ARCHITECT-PLAN.md`.

**Q: What are the three "go-to-90%" anchors?**
**Resilience (Stage 4)**, the **custom Kubernetes Operator (Stage 8)**, and **Observability/SRE (Stage 12)** — the places to reach genuine, defensible depth. See [[Learning Roadmap]].

**Q: How is progress tracked / handed off between sessions?**
`SESSION-HANDOFF.md` holds the current state-of-play so any session can resume. `CLAUDE.md` holds the working rules. Branches `main` and `dev` stay in sync.

**Q: Where do I actually start?**
Read the **[[Deliverables and Study Material|Learning Notes]]** for the concepts, pick your track (6- or 12-month) in [[Learning Roadmap]], then build **Stage 0.5** — application Python & testing foundations. One stage at a time; each must run before the next.

**Q: Why the name "Cosmos" and the 🔱?**
The platform orchestrates a vast, distributed "universe" of agents, providers, and events — Cosmos. The Learning Notes keep the trishul (🔱) as their mark; the rest of the project uses the 🌌 cosmos symbol.
