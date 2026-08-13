# Repository Structure

## Top-level layout

```
cosmos-llm-orchestration-platform/
├── app/                     # the Flask API (current) — Stage 0 rewrites this to FastAPI
├── tests/                   # test suite
├── docker-compose.yaml      # local containerized stack
├── Makefile · bootstrap.sh  # task wrappers
├── terraform/ · ansible/    # IaC (Module 4)
├── k8s/ · helm/ · argocd/   # Kubernetes + GitOps (Modules 5–6)
├── nginx/ · vagrant/ · postman/ · images/
├── docs/                    # module docs + the learning deliverables (see below)
└── *.md                     # the planning & learning docs (see doc map below)
```

## The planning & learning doc map

Read these in roughly this order:

| Doc | Role |
|---|---|
| [`README.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/README.md) | Front door — the current DevOps reference architecture + quick start |
| [`MASTER-BUILD-PROGRAM.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/MASTER-BUILD-PROGRAM.md) | ⭐ **The spine** — 16-track catalog, target architecture, the 12-stage build |
| [`LEARNING-PLAN.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/LEARNING-PLAN.md) | ⭐ **The calendar** — the ~56-week phased schedule |
| [`DEVOPS-CALIBRATION.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/DEVOPS-CALIBRATION.md) | ⭐ The program re-weighted 🟢/🟡/🔴 for the author's background |
| [`CLOUD-ARCHITECT-PLAN.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/CLOUD-ARCHITECT-PLAN.md) | Reference library + CSA framing + local-build tiers |
| [`SCALING-ROADMAP.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/SCALING-ROADMAP.md) | Phase-by-phase acceptance criteria for the early stages |
| [`STAGE-DESIGN-SPECS.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/STAGE-DESIGN-SPECS.md) | Per-stage build blueprint + Definition of Done |
| [`ARCHITECTURE-STUDY-GUIDE.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/ARCHITECTURE-STUDY-GUIDE.md) | 16-segment study companion |
| [`COVERAGE.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/COVERAGE.md) | What's covered vs. gaps; %-depth table |
| [`CLAUDE.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/CLAUDE.md) | Context + working rules for AI-assisted sessions |
| [`SESSION-HANDOFF.md`](https://github.com/akhil27051999/cosmos-llm-orchestration-platform/blob/main/SESSION-HANDOFF.md) | State-of-play so any session can continue the work |

## `docs/` — module docs + deliverables

- **Module docs:** `local-setup.md`, `app-testing.md`, `containerization.md`, `cicd.md`, `iac.md`, `k8s-orchestration.md`, `gitops.md`, `observability.md`, `git.md`, `aws.md`.
- **Learning deliverables** (see **[[Deliverables and Study Material]]**): `notes.html`, `architecture.html`, `roadmap.html`, `study-guide.html` + their `Cosmos-*.pdf` exports.

> **Branches:** `main` and `dev` are kept identical and pushed together. **Local folder:** `~/Desktop/cosmos`.
