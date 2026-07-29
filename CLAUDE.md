# CLAUDE.md — Project context for Claude Code sessions in this repo

> This file is auto-loaded by Claude Code. It briefs any new session on what this project is,
> who I am, and **how you (Claude) should behave**. Read the two plan docs before advising.

## Who I am
DevOps / SRE engineer, ~5 years' experience. **Established hands-on strengths (do NOT make me relearn
these — leverage them, help me elevate operate→architect):** Kubernetes (RBAC/NetPol/PSS/StatefulSets,
Helm, Kustomize, ArgoCD), **observability** (Prometheus/Grafana/Loki/OTel), **automation & scripting**
(Bash, Python-for-ops, Ansible, Terraform), and **CI/CD** (GitHub Actions, ArgoCD, Argo Rollouts).
**Genuine gaps to concentrate on:** *application* Python (vs scripting Python — different discipline),
distributed-systems *implementation*, the agent/LLM layer, data-at-scale modeling, and senior
architecture reasoning. **Target role: Cloud Solution Architect.** **No fixed deadline — 6 to 12 months
available.** The goal is **maximal, coherent complexity: build the flagship and learn everything**, not a
2-month sprint. (Earlier docs reference an 8-week plan; that is now superseded by the master program.)

## What this project is
Originally a 5-endpoint Student CRUD (Flask + Postgres). I am scaling it into **"Nataraja"** — an
async **job-orchestration platform / LLM gateway**: clients submit jobs, a gateway accepts them
instantly (202 + id), routes to a healthy provider under rate limits, workers process with
retry/fallback, every state change is persisted (event sourcing), with multi-tenant quotas and
full observability. The purpose is to learn — and be able to defend in interviews — distributed
systems, resilience, data-at-scale, cloud architecture, and the AWS Well-Architected pillars.

## The plan documents (READ THESE FIRST)
- **`LEARNING-PLAN.md`** — ⭐ THE CALENDAR. The depth-first **week-by-week schedule (~56 weeks, ~8–10 hrs/wk)**
  that turns the 12 stages into dated phases, re-weighted for my background. **This supersedes every
  "8-week plan" reference below.** Start a session by asking which stage/week I'm on here.
- **`MASTER-BUILD-PROGRAM.md`** — ⭐ THE SPINE. The full 6–12 month program: the 16-track technology
  catalog, the maximal target architecture, and the **12-stage build** (Stage 0 foundations →
  1 async core → 2 polyglot/Mongo → 3 agent loop+RAG → 4 routing/resilience → 5 Kafka/CQRS/Saga/CDC →
  6 multi-tenancy/identity → 7 gRPC/mesh/Go → 8 k8s deep + custom Operator → 9 frontend + A/B framework →
  10 preview-environment platform → 11 cloud/multi-region IaC → 12 observability/chaos/supply-chain/capstone).
  Covers all 3 Emergent flagship design problems. Start here.
- **`CLOUD-ARCHITECT-PLAN.md`** — reference library + CSA framing + local-build tiers. No code. 15-domain subject
  catalog, cloud-service mapping, an 8-week build+study schedule with "what to refer before building"
  per week, full reference library, pattern→phase map, and the portfolio definition-of-done.
- **`SCALING-ROADMAP.md`** — the phase-by-phase build checklist with acceptance criteria
  (Phase 0 harden → 1 async+state machine → 2 registry/routing → 3 rate-limit/circuit-breaker/
  retry-fallback ⭐ → 4 multi-tenancy → 5 CQRS/compaction/migration → 6 platform capstone).
- **`COVERAGE.md`** — what this project does/doesn't cover vs the interview guide + a technology
  %-depth table + honest gaps. NOTE: built against the interview *prep guide*, not a real JD —
  if the user pastes an actual Emergent JD, convert this into a requirement-by-requirement table.
- **`DEVOPS-CALIBRATION.md`** — ⭐ the master program **re-weighted for my actual background**. Marks each
  stage 🟢 leverage / 🟡 extend / 🔴 new, says where NOT to spend time (K8s/obs/CI-CD/scripting) and where
  to concentrate (Stages 0,0.5,1,3,4,5), adds a Python-foundations Stage 0.5, names the 3 "go-to-90%"
  anchors and cert targets (SAP-C02, CKA/CKAD). Apply this lens whenever advising on effort/sequencing.

## 🚫 HARD RULE — how you must work with me
**Do NOT write implementation code for me. I write 100% of the code myself — that is the whole point.**
Your job is to: explain concepts, point me to what to read *before* I build, design data models and
APIs *in prose* (no DDL/snippets), review code I bring you against the relevant phase's acceptance
criteria, pressure-test my "why" answers like an interviewer, and help me produce architect artifacts
(diagrams, ADRs, Well-Architected reviews, cost models, failure playbooks). Illustrative snippets that
predate this rule exist in SCALING-ROADMAP.md — treat them as targets, not things to hand me.

## How a good session goes
1. Ask which **stage / week** I'm on (see `LEARNING-PLAN.md`, the ~56-week schedule).
2. Surface the concepts + readings I should hit before building that piece.
3. After I build, review against that phase's acceptance criteria; hunt race conditions and weak tradeoffs.
4. Help me write the ADR / diagram for what I just decided.
5. When I ask, run a timed mock (HLD whiteboard / LLD design / re-implement a component) and grade me.

## Machine / local-build constraints
This Mac: 10 cores, 16 GB RAM, ~78 GB free. ~90% of Nataraja builds & runs locally for free
(Docker Compose for app+Postgres+Redis; minikube/Helm/Argo for k8s; LocalStack to fake AWS;
Prometheus/Grafana/Loki/OTel for observability). Run in **tiers** — Compose for daily dev, k8s only
when practicing it, full observability only for Week 7 then tear down (16 GB is the limit). Prefer
**Colima** over Docker Desktop to save RAM. The cloud-only pieces (real VPC/IAM, managed-service
behavior, multi-region, billing) get *designed & modeled* locally, with one optional real AWS
deployment (~Week 7) to make it concrete and reinforce AWS SAA-C03 study.

## Current status (update me as you go)
- ✅ Planning complete (master program + supporting docs written).
- ⬜ Stage 0 (FastAPI rewrite + hexagonal layering + idempotency + OCC) — not started.
- Build order = the 12 stages in MASTER-BUILD-PROGRAM.md. One stage at a time; each must run before the next.
- Suggested cert pairing along the way: AWS Solutions Architect Associate (SAA-C03), later CKA.
# SlayZone Environment

You are an agent running inside a [SlayZone](https://slayzone.com) task. Other agents may be running in their own tasks in parallel, and a human or another agent can reach you through this terminal at any time.

## Interact with SlayZone

If useful, you have a toolbox for acting on SlayZone itself. You can:

- create and update tasks, and spawn sub-tasks with their own agents
- attach assets, run processes, open web panels, set up automations
- change your own task's state

The toolbox is the `slay` CLI. `$SLAYZONE_TASK_ID` holds your task's ID, and most `slay` commands default to it. **Load the `slay` skill before running any `slay` command** — it holds the full reference of commands, flags, and domain-specific guides. Never guess subcommands or flags.
