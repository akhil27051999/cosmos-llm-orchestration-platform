# 0007: An SRE-focused roadmap

**Status:** Accepted, amended by [0008](0008-roadmap-skill-gaps.md) · **Date:** 2026-11-24 · **Scope:** whole project

## Context
I'm early in my SRE career, with five years in tech. This project is my main evidence of SRE skill, so its value
is in showing a system being **shipped, operated, measured and broken**, not only built. Time budget: ~20 h/week.

## Decision
Build → ship → operate, in this order:
1. **Part A, the system:** M6 Postgres (async SQLAlchemy, Alembic, Compose, optimistic concurrency) and Stage 1
   (Redis queue + worker, 202, at-least-once, retries, dead-letter queue).
2. **Part B, ship it:** S1 containers + Trivy/SBOM/cosign, S2 Helm + probes + PDB + HPA + KEDA on queue depth,
   S3 ArgoCD + Argo Rollouts canary + secrets out of Git.
3. **Part C, operate it:** S4 RED metrics, JSON logs, traces, dashboards; S5 two SLOs with multi-window burn-rate
   alerts and runbooks; S6 k6 load test, chaos (worker, DB, Redis) and a postmortem.
4. **Part D:** S7 the LLM as a flaky dependency (timeouts, retries with jitter, circuit breaker, rate limits, cost
   budget); S8 Terraform apply/demo/destroy.
- Parts B and C run on a **local kind/k3d cluster**; cloud only in S8.
- Built with an AI pair-programmer: Claude drafts, I review, explain back and own the decisions.

## Alternatives considered
- **Full LLM agent loop as a main stage:** interesting, but SRE interviews ask about dependencies failing, not agent
  design. Kept optional.
- **Ansible:** no VMs in this design, so it adds nothing.
- **Cloud from day one:** realistic, but costs money for every hour of learning.

## Consequences
- Estimate ~75–80 h (≈ 4 weeks). M6 + Stage 1 first, because Kubernetes can't scale an in-memory store.
- Every module adds to `docs/learning-log.md` and records its decisions here.
