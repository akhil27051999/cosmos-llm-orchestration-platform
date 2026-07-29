# DEVOPS-CALIBRATION.md — the build program, re-weighted for *your* starting point

> **Why this doc exists.** `MASTER-BUILD-PROGRAM.md` is the generic spine — it assumes you learn all
> 16 tracks from zero. You don't. You are a senior DevOps/SRE with real, hands-on expertise in
> **Kubernetes, observability, automation/scripting, and CI/CD**. This doc is the *lens*: it tells you
> where NOT to spend learning time (your strengths — compress and showcase them), and where to
> concentrate the energy you free up (your genuine gaps — application Python, distributed-systems
> *implementation*, the agent layer, data-at-scale, architecture reasoning).
>
> Read order: `MASTER-BUILD-PROGRAM.md` (what to build) → **this** (how hard each piece is *for you*,
> and where to go deep) → `SCALING-ROADMAP.md` (acceptance criteria) → `COVERAGE.md` (gaps).

---

## 1. Your established strengths — and the one reframe that matters most

| Strength | What you already have | What this means for the build |
|---|---|---|
| **Kubernetes** | RBAC, NetworkPolicies, PodSecurity, StatefulSets, Helm, Kustomize, ArgoCD — you *operate* clusters | Stage 8 mostly collapses. The only genuinely new thing is **writing a custom Operator/CRD** and **KEDA**. The rest is showcase. |
| **Observability** | Prometheus, Grafana, Loki, OTel collector — you *run* the stack | Stage 12 mostly collapses. The new work is **instrumenting your own application code** + **SLO/error-budget engineering from app metrics** + profiling. |
| **Automation & Scripting** | Bash, Python-for-ops, Ansible, Terraform — glue, infra, pipelines | This is a **bridge, not a substitute**, for application Python (see the reframe below). |
| **CI/CD** | GitHub Actions, ArgoCD, Argo Rollouts — you ship with these | Stage 8/12 CI work compresses. New work is **OIDC-to-cloud (keyless)**, **supply-chain security (SBOM/cosign/SLSA)**, and **progressive delivery with real metric analysis** wired to your SLOs. |

### ⚠️ The reframe that matters most: scripting Python ≠ application Python
You write Python to *automate infrastructure* (idempotent scripts, glue, CLI tools, Ansible modules).
The Helios core is *application* Python: long-lived async services, type-driven domain models, layered
architecture, concurrency primitives, test suites, ORMs. The skills transfer (you already think in
idempotency, retries, exit codes) but the **discipline is different**. This is your single biggest gap,
and it's why this doc adds **Stage 0.5** before the firehose.

---

## 2. The Leverage Map — every stage, re-weighted for you

**Tiers:** 🟢 **LEVERAGE** = you already operate this; the new work is to *author/extend/architect* it — go
fast, raise the bar to 90%, make it a showcase. 🟡 **EXTEND** = adjacent to what you know; moderate new
learning. 🔴 **NEW** = genuinely new domain; budget real time and don't rush it.

| Stage | Topic | Tier (for you) | What you already bring | What's genuinely new — spend time here |
|---|---|---|---|---|
| **0** | FastAPI rewrite, hexagonal, idempotency, OCC | 🔴 NEW | idempotency *instinct* from ops | async app structure, ports/adapters, OCC in code |
| **0.5** | **Python + testing foundations** *(added — see §4)* | 🔴 NEW | scripting fluency | typing, pytest, SQLAlchemy/Alembic, packaging |
| **1** | Async core: queue, state machine, event sourcing | 🔴 NEW | you've *operated* queues | building idempotent consumers, state machines in code |
| **2** | Polyglot persistence (Mongo, Redis) | 🟡 EXTEND | you've run these DBs | *modeling* (embed-vs-reference), aggregation, change streams |
| **3** | **Agent loop + RAG** ⭐ (Emergent core) | 🔴 NEW | nothing — fully new | agent loops, tool use, token budgets, embeddings, eval |
| **4** | **Resilience: rate-limit/breaker/retry/fallback** ⭐ | 🔴 NEW *impl*, 🟡 *concept* | you've watched breakers trip & tuned retries in Istio/Envoy | **implementing** them in code — connect ops intuition to LLD |
| **5** | Kafka + CQRS + Saga + CDC | 🔴 NEW | maybe operated Kafka | partitions/consumer-groups in code, CQRS, Saga, Debezium |
| **6** | Multi-tenancy, identity, Vault | 🟡 EXTEND | Vault/secrets *operationally* | OAuth2/OIDC/JWT app logic, tenant isolation, quotas |
| **7** | gRPC, **service mesh**, Go | mixed | **mesh 🟢** (you run Istio) | **Go 🔴**, **gRPC 🔴**; mesh new part = deliberate traffic-shaping |
| **8** | **K8s deep + custom Operator + KEDA** | 🟢 LEVERAGE | RBAC/NetPol/PSS/StatefulSets/Helm/Kustomize — *all yours* | **custom Operator/CRD (🔴, your top showcase)**, KEDA, policy authoring |
| **9** | Frontend + A/B framework | 🔴/🟡 | nothing on frontend | React/Next/TS 🔴; experimentation framework 🟡 |
| **10** | Per-tenant preview environments | 🟡 EXTEND | GitOps/K8s/ArgoCD — *yours* | vcluster + the provisioning controller (reuses your Stage-8 operator) |
| **11** | Cloud, networking, IaC, multi-region | mixed | **Terraform 🟢**, IaC discipline | AWS networking 🟡, **multi-region reasoning 🔴** |
| **12** | **Observability, SRE, chaos, supply-chain** | 🟢 LEVERAGE | Prom/Grafana/Loki/OTel — *all yours* | instrumenting **your own code**, **SLO engineering**, profiling, SBOM/cosign/SLSA |

### What the map tells you
- **Roughly half the program is 🟢/🟡 for you.** Stages **8, 10, 12**, the mesh half of **7**, and the
  Terraform mechanics of **11** are leverage — fly through the parts you know, spend your energy only on
  the genuinely-new slice of each.
- **Concentrate your real learning in Stages 0, 0.5, 1, 3, 4, 5.** That's application Python +
  distributed-systems *implementation* + the agent layer + data-at-scale. These are what a senior
  DevOps engineer is *missing* on the road to Cloud Architect.
- **The leverage stages are your fastest path to "architect," not your slowest.** Going from "I run a
  Grafana stack" to "I instrumented this system and defined its SLOs and error budgets" is the cleanest
  operate→architect upgrade you can show.

---

## 3. Your four strengths as woven "showcase tracks" (operate → architect)

Don't relearn these. Elevate each one level and make it visible across the build.

| Your strength | Current level | The architect-level move in Helios | Where it lands |
|---|---|---|---|
| **Kubernetes** | operate clusters | **author a custom Operator + CRD** that provisions tenants/preview-envs; admission policy as code | Stages 8 + 10 |
| **Observability** | run the stack | **instrument the system you built** end-to-end (OTel across async/Kafka/gRPC), define **SLOs + burn-rate alerts** from app metrics, profile hot paths | Stage 12 (uses 3,4,5) |
| **CI/CD** | ship with pipelines | **OIDC keyless deploys**, **supply-chain security** (SBOM/cosign/SLSA provenance), **progressive delivery with metric analysis** tied to your SLOs | Stages 8 + 12 |
| **Automation/Scripting** | infra glue | becomes **application Python** + **IaC modules with Terratest** + the operator's reconcile logic | Stages 0–1, 8, 11 |

**Interview framing for each:** "I didn't just operate X — I built the system it runs, instrumented it,
and defended every tradeoff." That sentence is the whole point of the program for someone with your
background.

---

## 4. Where the time you saved goes — the additions

Because ~half the program is leverage for you, reinvest that time in two places:

### Stage 0.5 — Python + testing foundations *(new; do before Stage 1)*
- **Build/learn:** the type system (annotations, `typing`, Pydantic v2), generators/coroutines vs
  `async`/`await`, context managers, decorators; **pytest** (fixtures, parametrize, mocking),
  `hypothesis` for property tests; **SQLAlchemy (async) + Alembic** migrations; dependency/venv hygiene
  with **uv** or Poetry; packaging.
- **Refer:** *Fluent Python* (Ramalho) ch. on data model + async; the FastAPI + SQLAlchemy async tutorial;
  pytest docs; `uv` docs. **Acceptance:** you can write a typed, tested async service module with a real
  migration and a meaningful test suite *before* you touch distributed systems.
- **Why:** you can't reason about the async race conditions in Stages 1/4 if the language and test
  discipline are shaky. This is the foundation the whole spine stands on.

### Go to 90% on three anchors (don't be 60%-everywhere)
A 6–7-YoE architect is deep in a few areas and conversant elsewhere. Pick these three to master:
1. **Stage 4 — resilience implementation.** Highest interview value; connects directly to your SRE
   intuition ("I've operated these; here's how I built them").
2. **Stage 8 — the custom Operator.** You can be world-class here *fast* because the K8s substrate is
   already yours. "I wrote a Kubernetes operator in Go" is a top-tier differentiator.
3. **Stage 12 — SLO/observability as architecture.** Elevates your strongest existing skill to architect
   level with the least friction.
Keep **Stage 3 (agents)** non-negotiable too — it's the Emergent core and fully new, so it needs real
time even though it isn't a "go to 90%" anchor.

---

## 5. Recalibrated pacing

Original: ~2 wk/stage (6-mo) or ~4 wk/stage (12-mo), uniform. Re-weighted for your leverage:

| Bucket | Stages | Relative effort |
|---|---|---|
| **Deep-new (full time, don't rush)** | 0, 0.5, 1, 3, 4, 5 | ~60% of total hours |
| **Extend (moderate)** | 2, 6, 9, the Go/gRPC half of 7, multi-region of 11 | ~30% |
| **Leverage (compress + showcase)** | 8, 10, 12, mesh of 7, Terraform of 11 | ~10% |

Net effect: the genuinely-new spine (0→5) is where you live for the first chunk; the back half moves
fast because it rides your existing infra muscle. **Spine first** still holds — Stages 0–5 truly owned
beats a sprawling half-finished Stage 10.

---

## 6. Certifications — aim higher than the master suggests
The master pairs SAA-C03 + CKA. Given your background:
- **CKA is nearly free for you** — you operate K8s daily. Knock it out early as a quick confidence win;
  consider **CKAD** too since you're now writing the apps that run on it.
- **Aim AWS Solutions Architect *Professional* (SAP-C02)**, not just Associate. For a 6–7-YoE architect
  role the Pro carries the signal that matches the depth you're building in Stage 11. Use SAA-C03 only as
  a stepping stone if the multi-service breadth is rusty.

---

## 7. The risk that outranks coverage (unchanged, restated for you)
Your strengths make the back half faster — but the front half (0–5) is genuinely hard and where most
solo learners stall. **A perfect Stage 4 circuit breaker beats a half-working Stage 7 mesh in any
interview.** Own the spine. Let the leverage stages be the victory lap they should be for someone with
your résumé.
