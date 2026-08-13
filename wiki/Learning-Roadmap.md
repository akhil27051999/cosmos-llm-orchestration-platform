# Learning Roadmap

The depth-first, week-by-week schedule that turns the 12 stages into dated phases — **re-weighted for the author's background** (fast through the leverage stages, deep on the genuinely new ones).

**Total: ~56 weeks (~13 months) at ~8–10 hrs/week**, deliberately unrushed. ~60% of the hours land in the **spine (weeks 1–29)**.

## Phases

| Phase | Weeks | Stage(s) | Tier | Focus |
|---|---|---|:--:|---|
| **A — Language & app discipline** | 1–7 | 0.5, 0 | 🔴 | The #1 gap: *application* Python ≠ scripting Python |
| **B — The distributed core** | 8–14 | 1, 2 | 🔴/🟡 | Queues, state machines, event sourcing *in code* |
| **C — The agent layer** ⭐ | 15–19 | 3 | 🔴 | The Emergent core; fully new |
| **D — Resilience** ⭐ #1 | 20–24 | 4 | 🔴 | SRE intuition → LLD you can defend |
| **E — Event-driven backbone** | 25–29 | 5 | 🔴 | Kafka/CQRS/Saga/CDC in code |
| **F — Multi-tenancy & identity** | 30–32 | 6 | 🟡 | OAuth2/OIDC app logic + isolation |
| **G — Internal comms & Go** | 33–36 | 7 | mixed | Go + gRPC new; mesh is leverage |
| **H — K8s deep + Operator** ⭐ #2 | 37–40 | 8 | 🟢 | Spend the weeks on the custom Operator + CRD |
| **I — Frontend + A/B framework** | 41–44 | 9 | 🔴/🟡 | React/Next/TS + experimentation |
| **J — Preview environments** | 45–47 | 10 | 🟡 | Reuses the Stage-8 operator + GitOps |
| **K — Cloud, IaC, multi-region** | 48–52 | 11 | mixed | Terraform mechanics yours; multi-region reasoning new |
| **L — Observability/SRE/chaos/capstone** ⭐ #3 | 53–56 | 12 | 🟢 | "I instrumented this system and set its SLOs" |

> **End of the spine (Week 29).** Own everything to here and you're already a different candidate.

## How the effort is distributed

- **🔴 Deep-new (~60% of hours):** Stages 0.5, 0, 1, 3, 4, 5 — application Python, distributed-systems *implementation*, the agent layer, data-at-scale.
- **🟢/🟡 Leverage/extend (~40%):** Stages 8, 10, 12, the mesh half of 7, the Terraform of 11 — go fast, raise the bar to 90%, make them showcases. **The leverage stages are the fastest path to "architect," not the slowest.**

## The three "go-to-90%" anchors

Interview-grade depth is concentrated in three places: **Resilience (Stage 4)**, the **custom Operator (Stage 8)**, and **Observability/SRE (Stage 12)**.

## See it as a board

Interactive roadmap (per-stage cards, progress tracking): [`docs/roadmap.html`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/roadmap.html) · PDF: [`docs/Cosmos-Roadmap.pdf`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/docs/Cosmos-Roadmap.pdf) · full calendar: [`LEARNING-PLAN.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/LEARNING-PLAN.md)

→ On compressing this to 2 months, see **[[FAQ]]**.
