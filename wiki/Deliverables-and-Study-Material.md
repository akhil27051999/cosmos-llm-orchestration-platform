# Deliverables and Study Material

Cosmos ships a self-contained study set — every concept in plain English, with analogies, diagrams, cheat-sheets, and self-checks. Each is a self-contained HTML page in `docs/` plus a light-theme PDF export.

| Deliverable | What it is | Files |
|---|---|---|
| 📓 **Learning Notes** | **97 lessons**, Foundations 0.5 → Stage 12, every concept at full depth (3-part explanations, 2 diagrams, analogy/insight/warning callouts, cheat-sheet, self-check). The main study artifact. | [`docs/notes.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/notes.html) · [`Cosmos-Notes.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Notes.pdf) |
| 🌌 **Interactive Architecture** | Click-through of the target system — Flow view + 3-D stack, plain-English cards per component. | [`docs/architecture.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/architecture.html) · [`Cosmos-Architecture.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Architecture.pdf) |
| 🌌 **Learning Roadmap** | The 56-week schedule as an interactive, trackable board (per-stage cards). | [`docs/roadmap.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/roadmap.html) · [`Cosmos-Roadmap.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Roadmap.pdf) |
| 📘 **Architecture Study Guide** | Exam-style companion to the architecture (16 segments). | [`docs/study-guide.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/study-guide.html) · [`Cosmos-Architecture-Study-Guide.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Architecture-Study-Guide.pdf) |

## Viewing tips

- **On GitHub:** the **PDFs render inline** — click any `Cosmos-*.pdf` above to read it in the browser. The `.html` files show as source on GitHub; to see them rendered, open them locally or via a static host / GitHub Pages.
- **The Learning Notes** are the recommended starting point — they teach the concepts behind every one of the 12 stages before you build them.

## What the Notes cover (Foundations 0.5 → Stage 12)

Python & async foundations → clean architecture & idempotency → async core (queues, state machines, event sourcing) → polyglot persistence → the agent loop + RAG → resilience (rate-limit/breaker/retry/fallback) → Kafka/CQRS/Saga/CDC → multi-tenancy & identity → gRPC/mesh/Go → Kubernetes + custom Operator → frontend + experimentation → preview environments → cloud/IaC/multi-region → observability/SRE/chaos/supply-chain.

→ See **[[The 12 Stage Build]]** for how these map to buildable increments.
