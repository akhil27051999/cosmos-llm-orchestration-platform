# Module 3: CI Pipeline with GitHub Actions (Self-Hosted Runner)

> **Goal:** On every push to `dev` or `main`, automatically run unit tests, build a Docker image, push it to DockerHub, and update the Helm chart's image tag in `main` so ArgoCD can deploy it.

> **Why this matters:** CI/CD is the heartbeat of any DevOps team. The pipeline is what makes "continuous deployment" possible — without it, every release is a manual, error-prone event. Knowing CI deeply (auth, runners, secrets, GitOps integration) is table-stakes for SRE roles.

---

## Table of Contents

1. [What This Pipeline Does](#what-this-pipeline-does)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Self-Hosted Runner vs GitHub-Hosted](#self-hosted-runner-vs-github-hosted)
4. [Pipeline Walkthrough](#pipeline-walkthrough)
5. [GitHub Secrets Required](#github-secrets-required)
6. [Pre-flight Checklist](#pre-flight-checklist)
7. [Commands Reference](#commands-reference)
8. [Troubleshooting](#troubleshooting)
9. [Interview Q&A](#interview-qa)
10. [STAR Stories](#star-stories)
11. [Production Hardening](#production-hardening)
12. [Cloud Mapping](#cloud-mapping)

---

## What This Pipeline Does

```
Developer pushes code → GitHub Actions triggers → builds → tests → 
publishes image → updates Git → ArgoCD picks up the change → 
K8s rolling update with new image
```

This is **CI handing off to GitOps CD**. CI builds artifacts; CD (ArgoCD) deploys them. They're decoupled but coordinated through Git.

---

## Architecture & Data Flow

```
GitHub                       Self-Hosted Runner               DockerHub               ArgoCD                  K8s Cluster
   │                                  │                            │                       │                          │
   │ developer pushes app/* code      │                            │                       │                          │
   ├─────────────────────────────────►│                            │                       │                          │
   │                                  │ checkout                   │                       │                          │
   │                                  │ python venv + pytest       │                       │                          │
   │                                  │ docker build               │                       │                          │
   │                                  │ docker push ──────────────►│                       │                          │
   │                                  │ sed update values.yaml     │                       │                          │
   │ ◄────────────────────── git push main (with [skip ci])        │                       │                          │
   │                                                               │                       │                          │
   │ ArgoCD polls main (every 3 min, or webhook)                   │                       │                          │
   ├──────────────────────────────────────────────────────────────────────►                │                          │
   │                                                                                       │ render Helm chart       │
   │                                                                                       │ apply new image tag ───►│
   │                                                                                       │                          │ rolling update
   │                                                                                       │                          │ → new pods running
```

**Key separation of concerns:**

| Job | Owns |
|-----|------|
| **build** | Tests + image build + push to registry |
| **update-helm** | Updates GitOps manifest (`helm/application/values.yaml`) |
| **ArgoCD (separate, see Module 6)** | Reconciles cluster state to match Git |

---

## Self-Hosted Runner vs GitHub-Hosted

| Aspect | GitHub-Hosted | Self-Hosted (what we use) |
|--------|---------------|---------------------------|
| **Cost** | Free for public repos; paid minutes for private | Hardware cost only |
| **Setup** | Zero — works out of box | Install + register runner; maintain it |
| **Network access** | Public internet only | Can reach private VPCs, internal services |
| **Secrets isolation** | Strong — fresh VM per job | Weaker — same machine reused, prior job leftovers |
| **Performance** | Fixed (2 vCPU, 7 GB) | Whatever you provision (GPU, big memory, fast disk) |
| **Caching** | Per-job (use `actions/cache`) | Persistent local FS — fast pip/docker layer caches |
| **Compliance** | Code runs in GitHub's cloud | Code stays in your environment |

**When to use self-hosted:**
- Need access to internal services (DB, S3 with private VPC endpoints)
- Heavy workloads (long builds, GPU inference)
- Strict compliance / data residency
- Cost optimization (free for personal use)

**Why we used self-hosted here:** the runner is our local Mac — convenient for learning, plus has Docker Desktop pre-running.

### Setting Up a Self-Hosted Runner (macOS)

| Step | Action | Command |
|------|--------|---------|
| 1 | GitHub repo → Settings → Actions → Runners → New self-hosted runner → macOS ARM64 | (UI) |
| 2 | Download | `mkdir actions-runner && cd actions-runner` |
| 3 | Extract | `tar xzf ./actions-runner-osx-arm64-*.tar.gz` |
| 4 | Configure | `./config.sh --url https://github.com/<user>/<repo> --token <token>` |
| 5 | Start | `./run.sh` |
| 6 | Verify | repo Settings → Actions → Runners shows your runner as "Idle" |

**Runner is online while `./run.sh` is running.** For background/persistent: install as a service (`./svc.sh install && ./svc.sh start`).

---

## Pipeline Walkthrough

### Triggers ([ci-pipeline.yaml:3-16](../.github/workflows/ci-pipeline.yaml))

```yaml
on:
  push:
    branches: [dev, main]
    paths: ['app/**']
  pull_request:
    branches: [dev, main]
    paths: ['app/**']
  workflow_dispatch:
```

| Trigger | When |
|---------|------|
| `push` to `dev` / `main` (only `app/**`) | Code change in app folder |
| `pull_request` to `dev` / `main` (only `app/**`) | PR opened/updated touching app |
| `workflow_dispatch` | Manual trigger from Actions UI |

**Why path filter `app/**`?** Avoids unnecessary CI runs when only docs/helm/argocd files change. Keeps the cycle fast and CI minutes cheap.

---

### Job 1 — `build`

```yaml
build:
  runs-on: self-hosted
  outputs:
    image_tag: ${{ steps.build-image.outputs.image_tag }}
```

**`outputs`** — `image_tag` is exposed to downstream jobs (`update-helm` consumes it).

**Steps:**

| Step | What | Why |
|------|------|-----|
| Checkout | `actions/checkout@v4` | Pulls the repo at the triggering commit |
| Install Dependencies | Create venv, `pip install -r requirements.txt` | Isolates deps; works on system Python (no `setup-python` action needed) |
| Run Tests | `pytest -v tests/unit` | Catches regressions before building image |
| Build Docker Image | `docker build -t flask-app:${SHA::7} .` | SHA-based immutable tag |
| Login to DockerHub | `docker/login-action@v3` | Uses repo secrets |
| Push Docker Image | `docker push <user>/flask-app:$TAG` | Makes it available for K8s to pull |
| Cleanup | `docker rmi` | Frees disk on the (persistent) self-hosted runner |

**Image tagging strategy:** `${GITHUB_SHA::7}` = first 7 chars of commit SHA (e.g., `a507bff`). Immutable, traceable to a specific commit. Avoid `latest` in production.

---

### Job 2 — `update-helm`

```yaml
update-helm:
  needs: build
  runs-on: self-hosted
```

**`needs: build`** — runs only after `build` succeeds; receives `image_tag` output.

**Steps:**

| Step | What | Why |
|------|------|-----|
| Checkout main branch | `actions/checkout@v4` with `ref: main`, `fetch-depth: 0`, `token: GH_PAT` | Always operate on main (regardless of trigger branch). Full history needed to push. PAT has `workflow` scope. |
| Configure Git | Set user.name / user.email | Required for commits |
| Update image tag | `sed -i.bak "s\|...\|$IMAGE_TAG\|" helm/application/values.yaml` | Cross-platform sed (works on macOS + Linux) |
| Commit and push | `git commit -m "ci: ... [skip ci]" && git push origin main` | `[skip ci]` prevents trigger loops |

**Why explicit `ref: main`?** Without it, the checkout uses the trigger branch (could be `dev`). Then pushing would push `dev` to `main` — disaster. Always be explicit when CI writes back to a specific branch.

**Why `[skip ci]` in commit message?** GitHub Actions skips workflows for commits with this marker. Path filter `app/**` already prevents the loop (since this commit only changes `helm/`), but `[skip ci]` is belt-and-suspenders.

---

## GitHub Secrets Required

| Secret | Purpose | How to Create |
|--------|---------|---------------|
| `DOCKER_HUB_USERNAME` | DockerHub login | Your DockerHub username |
| `DOCKER_HUB_ACCESS_TOKEN` | DockerHub auth | DockerHub → Account Settings → Security → New Access Token |
| `GH_PAT` | Push to `main` from CI (default `GITHUB_TOKEN` lacks `workflow` scope) | GitHub → Settings → Developer settings → Personal access tokens → Generate (classic) → enable `repo` + `workflow` scopes |

**Why a separate PAT?** The default `GITHUB_TOKEN` is restricted — it can read/write code but **cannot modify workflow files**. If you ever change the workflow itself in the same commit, the push fails. PAT bypasses that.

---

## Pre-flight Checklist

| Check | Command | Why |
|-------|---------|-----|
| Self-hosted runner online | `ps aux \| grep Runner.Listener \| grep -v grep` | Workflow waits forever if runner offline |
| Docker Desktop running | `docker ps` | Build/push steps need Docker daemon |
| Python deps install | `cd app && pip install -r requirements.txt` (in clean venv) | Catches incompatible packages early |
| Unit tests pass locally | `pytest -v tests/unit` | Don't waste CI time on broken tests |
| All secrets present | GitHub repo Settings → Secrets | Pipeline fails at first usage if missing |
| `helm/application/values.yaml` has a `tag:` line for sed to match | `grep "tag:" helm/application/values.yaml` | sed silently does nothing if pattern doesn't match |

---

## Commands Reference

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Start self-hosted runner | `cd actions-runner && ./run.sh` | Foreground; runner picks up jobs |
| 2 | Kill stale runner sessions | `pkill -f Runner.Listener` | Frees registration if `run.sh` was suspended |
| 3 | Manually trigger workflow | `gh workflow run "REST-API-CI-Pipeline" --ref main` | Without code change |
| 4 | List recent runs | `gh run list --limit 5` | Quick check from CLI |
| 5 | Watch live | `gh run watch` | Tail an in-progress run |
| 6 | View logs | `gh run view --log` | Inspect failure |
| 7 | Verify DockerHub push | `docker pull <user>/flask-app:<tag>` | Confirm image is in registry |
| 8 | Force ArgoCD sync after CI | `kubectl patch application flask-api -n argocd --type merge -p '{"operation":{"sync":{"revision":"main"}}}'` | Skip the 3-min poll wait |
| 9 | Inspect updated values.yaml | `git log helm/application/values.yaml` | See CI's commits |
| 10 | Erase cached creds (if PAT changes) | `git credential-osxkeychain erase` | Clear stale macOS keychain entry |

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | `mkdir: /Users/runner: Permission denied` | `actions/setup-python@v4` tries to install at `/Users/runner` (only exists on GitHub-hosted runners) | Skip `setup-python`; use system `python3` with venv |
| 2 | `Input required and not supplied: token` | `GH_PAT` secret missing | Add it under Settings → Secrets → Actions |
| 3 | `sed: invalid command code` (macOS) | macOS sed requires `-i ''`; Linux uses `-i` alone | Use cross-platform: `sed -i.bak "s|...|" file && rm -f file.bak` |
| 4 | `git push: refusing to allow PAT without workflow scope` | PAT lacks `workflow` scope | Edit PAT in Developer settings; add `workflow` scope |
| 5 | `Authentication failed` after PAT update | Old PAT cached in keychain | `git credential-osxkeychain erase`; re-enter creds |
| 6 | `A session for this runner already exists` | Suspended `./run.sh` (Ctrl+Z) not killed | `pkill -f Runner.Listener && ./run.sh` |
| 7 | `ModuleNotFoundError: locust` during pytest | `tests/load_test.py` imports Locust (not in CI deps) | Limit pytest scope: `pytest -v tests/unit` |
| 8 | `Push declined due to repository rule violations` | GitHub Push Protection detected a secret | Use the bypass URL in the error OR rewrite history (`git reset --soft HEAD~N && git commit`) and remove the secret |
| 9 | `! [rejected] main -> main (fetch first)` from `update-helm` push | Remote moved (e.g., another PR merged) | First job: `git pull --rebase origin main` before push; or use `git push --force-with-lease` if owning sole writer |
| 10 | Workflow runs but no Helm update | `update-helm` checked out wrong branch | Set `ref: main` explicitly in checkout |
| 11 | Infinite trigger loop | CI commit retriggered CI | Use `paths:` filter (`app/**` excludes `helm/**`) AND `[skip ci]` in commit message |
| 12 | DockerHub `denied: requested access to the resource is denied` | Wrong credentials | Verify `DOCKER_HUB_USERNAME` (your username, not email) and access token |
| 13 | Node 20 deprecation warnings | Old action versions | Upgrade `actions/checkout@v3 → v4`, `docker/login-action@v2 → v3` |
| 14 | Pytest fails: `Duplicated timeseries in CollectorRegistry` | `prometheus-flask-exporter` `metrics.info()` registers globally; tests create app multiple times | Drop the `metrics.info()` call (covered in Module 1B) |

---

## Interview Q&A

| Q | A |
|---|---|
| **What's the difference between CI and CD?** | CI (Continuous Integration) = build, test, package on every commit. CD (Continuous Delivery/Deployment) = automatically deploy passing builds. CI ends at the artifact; CD picks it up. |
| **Why GitHub Actions vs Jenkins?** | GHA = no infra to maintain, deeply integrated with GitHub, YAML-as-code. Jenkins = self-hosted, plugin ecosystem, more flexibility for legacy/complex pipelines. Both are valid; GHA is more popular for new projects. |
| **What's a self-hosted runner?** | Your own compute (VM, container, bare metal) registered with GitHub to execute jobs. Use when you need private network access or custom hardware. |
| **Risks of self-hosted runners?** | Persistent state across jobs (leftovers); lower isolation than ephemeral GitHub-hosted runners; runner compromise = code execution; OS/Docker updates needed. **Best practice:** ephemeral runners (recreated per job) via tools like actions-runner-controller for K8s. |
| **What's the matrix strategy?** | Run the same job across multiple variants (e.g., Python 3.10/3.11/3.12 × Linux/Mac). `strategy: matrix:` block in YAML. Used for cross-version testing. |
| **What's `workflow_dispatch`?** | Manual trigger from the Actions UI. Useful for ad-hoc deploys, debugging, force redeploys. |
| **What's `[skip ci]`?** | Special string in commit message that GitHub honors by skipping CI workflows for that commit. Prevents trigger loops. |
| **Why use SHA-based image tags instead of `latest`?** | Reproducibility — `latest` is mutable. SHA is immutable, lets you pin and roll back exact builds. **Never** use `latest` in K8s production manifests. |
| **What does `needs:` do?** | Defines job dependencies. `needs: build` makes `update-helm` wait for `build` to succeed; failures upstream halt the workflow. |
| **What's the difference between `secrets.GITHUB_TOKEN` and a PAT?** | `GITHUB_TOKEN` is auto-issued per workflow, limited scope (can't modify `.github/workflows/*`). PAT (Personal Access Token) is user-issued, broader scopes (e.g., `workflow`), used when you need to bypass restrictions. |
| **How do you handle secrets in CI?** | GitHub Secrets (encrypted at rest, masked in logs). Never echo them. Prefer OIDC for cloud auth (short-lived tokens, no static creds). |
| **What's OIDC in GitHub Actions?** | OpenID Connect federation — GitHub Actions can assume an AWS/GCP/Azure IAM role without long-lived keys. Industry-best for cloud auth. |
| **How do you parallelize jobs?** | Multiple jobs at the top level run in parallel by default. Use `needs:` to serialize when needed. Within a job, steps run sequentially. |
| **What's a reusable workflow?** | A workflow file that other workflows can call (`uses: org/repo/.github/workflows/x.yml@v1`). Reduces duplication across repos. |
| **What's a composite action?** | A custom action made of multiple steps, packaged as a reusable unit. Lives in `.github/actions/<name>/action.yml`. |
| **How do you cache dependencies in GHA?** | `actions/cache@v4` with a key based on lockfile hash. E.g., `key: pip-${{ hashFiles('**/requirements.txt') }}`. Saves minutes on dependency install. |
| **What's a pull-based vs push-based CD?** | Push (CI directly applies to cluster) — CI needs cluster credentials. Pull (GitOps) — controller in cluster pulls changes from Git; CI never touches cluster. We use pull (ArgoCD). |
| **How would you implement blue/green or canary in this pipeline?** | Build one image. For canary: ArgoCD Rollouts CRD with `setWeight: 10` → wait → `setWeight: 50`. For blue/green: two ArgoCD apps (blue/green), switch traffic via service selector. |
| **How do you debug a failed self-hosted runner job?** | SSH to the runner machine; check `actions-runner/_diag/` logs; verify Docker daemon, network, secrets. For ephemeral runners, debug via `tmate` (`mxschmitt/action-tmate@v3` step). |
| **How do you ensure CI doesn't take forever?** | Path filters; cache deps; parallelize jobs; pin smaller base images for tests; split tests across shards (`pytest-xdist`); fail fast (`-x`). |

---

## STAR Stories

### Story 1: "Tell me about a time a CI pipeline broke after a tooling upgrade."

**Situation:** After upgrading our CI workflow to use a self-hosted runner on macOS, every run failed at the `Set up Python` step with `mkdir: /Users/runner: Permission denied`.

**Task:** Make the pipeline portable across runner types without losing test isolation.

**Action:**
1. Recognized that `actions/setup-python@v4` hardcodes `/Users/runner/...` paths — only valid on GitHub-hosted Linux runners.
2. Two options: (a) switch back to GitHub-hosted, or (b) drop `setup-python` and use the runner's system Python.
3. Chose (b) since the macOS host already had Python 3.12. Replaced the step with a venv setup: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`.
4. Updated subsequent steps to source the venv before each Python invocation.

**Result:** Pipeline ran end-to-end on the self-hosted runner. As a side benefit, dependency caching is now automatic on the persistent runner — pip uses its local cache.

**Takeaway:** GitHub-curated actions assume their hosted runner image; verify behavior on self-hosted before adopting. Sometimes plain shell is more portable than a marketplace action.

---

### Story 2: "Tell me about a time you handled a leaked secret."

**Situation:** I accidentally committed a Slack webhook URL to `helm/prometheus/values.yaml` (for Alertmanager). On `git push`, GitHub Push Protection blocked it with: "Push cannot contain secrets."

**Task:** Get the change in without leaking the webhook permanently to git history.

**Action:**
1. Read GitHub's error — it offered a "bypass" URL but warned the secret would be saved to history.
2. Slack also auto-revoked the webhook because GitHub notified them (cross-platform secret scanning).
3. Decision: rewrite history so the webhook never lands in main.
4. Squashed the bad commit + the fix commit into one clean commit using `git reset --soft HEAD~2 && git commit -m "..."`.
5. Re-architected the secret handling: created a K8s Secret out-of-band (`kubectl create secret generic alertmanager-slack-webhook ...`); referenced it via `slack_api_url_file: /etc/alertmanager/secrets/slack_url` in Alertmanager config; mounted via `extraSecretMounts`.
6. Generated a fresh webhook URL in Slack and stored only in the K8s secret — never in Git.

**Result:** Push succeeded. Webhook never touched Git history. Pattern documented for future contributors: "Secrets go in K8s Secrets / Vault / SSM — never values.yaml."

**Takeaway:** Push Protection caught a real mistake; the fix is to architect secrets out of git, not bypass the protection. Always rotate any secret that leaks, even momentarily.

---

### Story 3: "Tell me about a time CI pushed to the wrong branch."

**Situation:** Our `update-helm` job was pushing the new image tag commit to `dev` instead of `main` whenever CI was triggered by a `dev` push.

**Task:** Fix the GitOps loop — ArgoCD watches main, so updates must land in main.

**Action:**
1. Inspected the workflow — `actions/checkout@v4` was using the default behavior: checkout the **trigger branch**.
2. Then `git push origin main` actually pushed the trigger branch's HEAD into `main` (which could overwrite main's history).
3. Added explicit `ref: main` and `fetch-depth: 0` to the checkout step.
4. Added a `token: ${{ secrets.GH_PAT }}` because default `GITHUB_TOKEN` couldn't push when workflow files exist in the repo.
5. Tested by pushing to `dev` — image built from dev's code, but `helm/application/values.yaml` was updated on `main`.

**Result:** GitOps loop now correct: any branch's CI builds an image; main's manifest gets the tag; ArgoCD redeploys.

**Takeaway:** Always be explicit with `ref:` in checkout when CI writes back to git. Default behaviors change subtly across actions and can ruin your day.

---

## Production Hardening

| Area | Current | Production |
|------|---------|-----------|
| **Runner type** | Long-lived self-hosted | Ephemeral runners (one job per runner) via `actions-runner-controller` on K8s |
| **Image scanning** | None | Trivy / Snyk step on every build; fail on critical CVEs |
| **SBOM** | None | Generate Software Bill of Materials with Syft; attach as build artifact |
| **Image signing** | None | Cosign signing in CI; admission controller verifies in cluster |
| **Cloud auth** | Static DockerHub token | OIDC federation to AWS/GCP — short-lived tokens, no static creds |
| **Test isolation** | Real tests with SQLite | Add integration tests with real Postgres (testcontainers) and contract tests (Pact) |
| **Branch protection** | None | Require CI passing + 1 reviewer before merge to main |
| **Required status checks** | None | Block PR merge unless `build` job passes |
| **Pinning action versions** | Tag (`@v4`) | Pin to commit SHA for supply-chain security |
| **Caching** | None | `actions/cache` for pip + docker layer caching (BuildKit) |
| **Notifications** | None | Slack on failure; Slack on production deploy |
| **Coverage reporting** | None | `pytest --cov` + Codecov / Coveralls |
| **Multi-arch images** | linux/arm64 only (Mac runner) | `docker buildx` for amd64 + arm64 |
| **Test parallelism** | Sequential | `pytest-xdist`; matrix strategy for Python versions |
| **Approval gates** | Auto-merge on push | Require manual approval for prod values changes |

---

## Cloud Mapping

| GitHub Actions | AWS | GCP | Azure |
|---------------|-----|-----|-------|
| GitHub Actions | CodePipeline + CodeBuild | Cloud Build | Azure Pipelines / DevOps |
| GitHub-hosted runner | CodeBuild managed runner | Cloud Build worker | Microsoft-hosted agent |
| Self-hosted runner | EC2 with CodeBuild agent | GCE with custom worker | VM Scale Set with agent |
| GitHub Container Registry (GHCR) | ECR | Artifact Registry | ACR |
| GitHub Secrets | Secrets Manager / SSM | Secret Manager | Key Vault |
| OIDC to AWS | `aws-actions/configure-aws-credentials` (assume role) | Workload Identity Federation | Federated identity |
| `actions/cache` | CodeBuild cache (S3) | Cloud Build cache | Pipeline cache |

---

## CI + GitOps: The Big Picture

The full lifecycle from code change to running pod:

| Step | Owned By | Action |
|------|----------|--------|
| 1 | Developer | `git push origin dev` (app code change) |
| 2 | GitHub Actions (`build`) | Test, build image, push `<user>/flask-app:<sha7>` |
| 3 | GitHub Actions (`update-helm`) | sed `helm/application/values.yaml` tag → commit to `main` |
| 4 | ArgoCD (Module 6) | Detects values.yaml diff on main, renders new manifests |
| 5 | Kubernetes | Rolling update — old pods drained, new pods come up with new image |
| 6 | Operator (you) | Verify with `kubectl rollout status` and Grafana dashboards |

This is the **pull-based GitOps** model — CI never touches the cluster directly. Git is the single source of truth.

---

## Reference Links (Internal)

- Workflow: [.github/workflows/ci-pipeline.yaml](../.github/workflows/ci-pipeline.yaml)
- Dockerfile (consumed by build): [app/Dockerfile](../app/Dockerfile)
- Helm values (updated by `update-helm`): [helm/application/values.yaml](../helm/application/values.yaml)
- Tests run by CI: [tests/unit/](../tests/unit/)
