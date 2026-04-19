# Module 6: GitOps with Helm + ArgoCD

> **Goal:** Package the K8s manifests as **Helm charts** for templating and versioning, then deploy them via **ArgoCD** with the **App-of-Apps pattern** so a single root app manages everything in the cluster.

> **Why this matters:** GitOps is the dominant deploy model for K8s in 2025. Helm + ArgoCD is the most common combo. SREs are expected to know how Helm templates render, how ArgoCD reconciles, why pull-based deploys are safer than push, and how to debug sync issues.

---

## Table of Contents

1. [Why GitOps](#why-gitops)
2. [Why Helm](#why-helm)
3. [Architecture](#architecture)
4. [Part A — Helm Deep Dive](#part-a--helm-deep-dive)
5. [Part B — ArgoCD Deep Dive](#part-b--argocd-deep-dive)
6. [The CI → GitOps → Deploy Loop](#the-ci--gitops--deploy-loop)
7. [Commands Reference](#commands-reference)
8. [Troubleshooting](#troubleshooting)
9. [Interview Q&A](#interview-qa)
10. [STAR Stories](#star-stories)
11. [Production Hardening](#production-hardening)
12. [Cloud Mapping](#cloud-mapping)

---

## Why GitOps

| Manual `kubectl apply` | GitOps |
|------------------------|--------|
| Anyone with kubeconfig can change cluster | Only Git PRs change cluster |
| No audit trail beyond `kubectl audit` | `git log` = full deployment history |
| Drift between cluster and intended state | ArgoCD detects + auto-syncs drift |
| Rollback = `kubectl rollout undo` (per resource) | Rollback = `git revert` (everything) |
| CI needs cluster credentials | Cluster pulls from Git — no creds in CI |
| Manual coordination across services | Declarative — describe end state |

### Push vs Pull CD

| Push (CI applies to cluster) | Pull (GitOps controller in cluster) |
|------------------------------|------------------------------------|
| CI has cluster credentials | Cluster has read-only Git access |
| Direct, immediate | Eventual (3-min poll or webhook) |
| Hard to audit | Git history = audit |
| Network: CI → cluster (firewall complexity) | Network: cluster → Git (simpler) |
| **Examples:** `kubectl apply` from GHA, Spinnaker | **Examples:** ArgoCD, Flux |

**The big win for pull-based:** the cluster's "desired state" lives in Git. Even if your laptop, CI, and console are all gone, the cluster reconciles itself.

---

## Why Helm

Raw K8s YAML has problems at scale:
- **No templating** — duplicate `metadata.namespace`, image tags, labels everywhere
- **No environments** — dev/staging/prod need different replicas, image tags, resources
- **No versioning** — what version is deployed? When did it change?
- **No releases** — installing 20 manifests = 20 separate `kubectl apply` calls

Helm solves all of these.

| Problem | Helm Solution |
|---------|---------------|
| Duplication | Templates with `{{ .Values.x }}` |
| Per-env config | Multiple `values.yaml` files (`-f values-prod.yaml`) |
| Versioning | Each install = a versioned release; rollback supported |
| Multi-resource | One chart = many manifests; one `helm install` |
| Reuse | Charts published to repos (Artifact Hub); pull and customize |

---

## Architecture

### App-of-Apps Pattern (What We Use)

```
                            argocd namespace
                                  │
                       ┌──────────┴──────────┐
                       │  root-app           │
                       │  (Application)      │
                       │  watches: argocd/   │
                       │  excludes:          │
                       │     root-app.yaml   │
                       └──────────┬──────────┘
                                  │ creates these Applications:
        ┌──────────┬──────────────┼──────────────┬──────────────┐
        │          │              │              │              │
   ┌────▼────┐┌────▼────┐ ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼─────┐
   │ vault   ││external-│ │ database    │ │ flask-api│ │ observ.    │
   │         ││ secrets │ │             │ │          │ │ apps × 6   │
   │ helm/   ││ helm/   │ │ helm/       │ │ helm/    │ │ Module 7   │
   │ vault/  ││ external│ │ database/   │ │ application│
   │         ││ -secrets│ │             │ │          │ │            │
   └─────────┘└─────────┘ └─────────────┘ └──────────┘ └────────────┘
        │           │             │              │             │
        ▼           ▼             ▼              ▼             ▼
     vault ns  external-     student-api ns  student-api    observability ns
               secrets ns                    ns             (Prom, Loki, etc.)
```

**Bootstrap = single command:**
```bash
kubectl apply -f argocd/root-app.yaml
```

ArgoCD takes over from there — pulls Git, renders charts, applies everything.

---

## Part A — Helm Deep Dive

### Chart Structure (Industry Standard)

```
helm/application/
├── Chart.yaml          # Metadata: name, version, appVersion
├── values.yaml         # Default values
└── templates/
    ├── _helpers.tpl    # Named template helpers (no leading _: not rendered)
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    └── NOTES.txt       # Printed after install (helm install output)
```

### Chart.yaml

```yaml
apiVersion: v2
name: flask-api
description: Flask REST API
type: application
version: 0.1.0          # Chart version (independent of app)
appVersion: "7.0.0"     # Version of the app being deployed
```

| Field | Purpose |
|-------|---------|
| `apiVersion: v2` | Helm 3 chart format |
| `version` | The chart version. Bump on chart changes. Used by `helm install`/`upgrade`. |
| `appVersion` | The app version (e.g., flask-api v7.0.0). Cosmetic; surfaces in `helm list`. |
| `dependencies` | Sub-charts to pull (e.g., postgres). Run `helm dependency update`. |

### values.yaml — The Defaults

```yaml
app:
  name: flask-api
  image:
    repository: akhilthyadi/flask-app
    tag: 7.0.0
    pullPolicy: IfNotPresent
  replicaCount: 2
  service:
    type: NodePort
    port: 80
    targetPort: 5000
  nodeSelector:
    type: application
```

Everything that varies per-environment goes here.

### Template — The Magic

`templates/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.app.name }}
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "student-api.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.app.replicaCount }}
  template:
    spec:
      containers:
        - name: {{ .Values.app.name }}
          image: "{{ .Values.app.image.repository }}:{{ .Values.app.image.tag }}"
          imagePullPolicy: {{ .Values.app.image.pullPolicy }}
```

**Built-in objects available in templates:**

| Variable | Value | Example |
|----------|-------|---------|
| `.Values` | values.yaml + `--set` overrides | `.Values.app.image.tag` |
| `.Release.Name` | The release name | `student-api` |
| `.Release.Namespace` | Where it's installed | `student-api` |
| `.Chart.Name` | From Chart.yaml | `flask-api` |
| `.Chart.Version` | Chart version | `0.1.0` |
| `.Chart.AppVersion` | App version | `7.0.0` |
| `.Files` | Files in the chart (use `.Files.Get`) | Reading non-template files |
| `.Capabilities` | Cluster info (K8s version, available APIs) | `.Capabilities.KubeVersion` |
| `.Template` | Current template name + path | Debugging |

### Template Functions

Helm uses Go templates + Sprig functions + Helm-specific functions:

```yaml
# Default value if missing
{{ .Values.app.image.tag | default "latest" }}

# Trim whitespace + indent
{{- toYaml .Values.app.nodeSelector | nindent 8 }}

# Conditional
{{- if .Values.app.ingress.enabled }}
# ... ingress YAML ...
{{- end }}

# Loop
{{- range .Values.app.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
```

**`{{-` and `-}}`** — strip leading/trailing whitespace. Critical for clean YAML output.

### Named Templates (Helpers)

`templates/_helpers.tpl`:
```yaml
{{- define "student-api.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: Helm
{{- end -}}
```

Used in deployment.yaml:
```yaml
metadata:
  labels:
    {{- include "student-api.labels" . | nindent 4 }}
```

`include` invokes the template; `nindent 4` indents output by 4 spaces.

### Where Helm Stores Releases

Each release is stored as a Kubernetes Secret in the release namespace:

```bash
kubectl get secret -n student-api -l owner=helm
# sh.helm.release.v1.student-api.v1   helm.sh/release.v1   1   3h
```

The secret contains the rendered manifests + values for that revision. `helm rollback` restores from this secret.

### Helm Hooks

Run K8s resources at lifecycle points:

| Hook | When |
|------|------|
| `pre-install` | Before any resources are created |
| `post-install` | After all resources are created |
| `pre-upgrade` / `post-upgrade` | Around upgrades |
| `pre-delete` / `post-delete` | Around uninstall |
| `test` | When `helm test <release>` is run |

Example — DB seed Job after install:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-db
  annotations:
    "helm.sh/hook": post-install
    "helm.sh/hook-delete-policy": hook-succeeded   # cleanup after success
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: seed
          image: akhilthyadi/flask-app:7.0.0
          command: ["sh", "-c", "PYTHONPATH=/api python /api/seed.py"]
```

### Sub-charts (Dependencies)

```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: 13.x.x
    repository: https://charts.bitnami.com/bitnami
```

```bash
helm dependency update helm/application
```

Pulls postgres as a sub-chart. Saves you from maintaining your own Postgres chart.

### Multi-Environment Pattern

```bash
helm install student-api helm/application \
  -f helm/application/values.yaml \
  -f helm/application/values-prod.yaml   # overrides for prod
```

Or per-env values directories:
```
helm/application/
├── values.yaml         # base
├── values-dev.yaml     # dev overrides
├── values-staging.yaml
└── values-prod.yaml
```

Last `-f` wins on conflicts.

### `helm template` vs `helm install --dry-run`

| Command | Difference |
|---------|-----------|
| `helm template` | Renders client-side only. No API server contact. Fast. |
| `helm install --dry-run` | Renders + sends to API server for validation. Catches schema/admission errors. |

Use `template` for quick iteration; use `--dry-run` before real install.

---

## Part B — ArgoCD Deep Dive

### What ArgoCD Is

A K8s controller that watches Git repos and reconciles cluster state to match. **Git is the single source of truth.**

### ArgoCD Components (Pods)

| Component | Role |
|-----------|------|
| `argocd-server` | API + web UI |
| `argocd-application-controller` | The reconciliation engine — diffs Git vs cluster, applies |
| `argocd-repo-server` | Clones Git, renders Helm/Kustomize |
| `argocd-redis` | Caching layer |
| `argocd-applicationset-controller` | Generates Applications dynamically (advanced) |
| `argocd-notifications-controller` | Slack/email on sync events |
| `argocd-dex-server` | OIDC SSO integration |

### Install ArgoCD

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

helm install argocd argo/argo-cd \
  -n argocd --create-namespace

# Get admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8081:443
# Open https://localhost:8081 (admin / <password>)
```

### Application — The Core CRD

The `Application` is the unit of GitOps. It says "watch this Git path; render it; apply to this destination."

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: student-api
  namespace: argocd                    # ArgoCD always lives here
spec:
  project: default
  source:
    repoURL: https://github.com/akhil27051999/Flask-REST-API.git
    targetRevision: main               # branch / tag / commit SHA
    path: helm/application             # folder in repo
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc   # in-cluster
    namespace: student-api
  syncPolicy:
    automated:
      prune: true                      # delete resources removed from Git
      selfHeal: true                   # revert manual changes
    syncOptions:
      - CreateNamespace=true           # create dest ns if missing
      - ServerSideApply=true           # better for large CRDs
```

### Sync Policy Options

| Option | Effect | When to Use |
|--------|--------|-------------|
| `automated.prune: true` | Delete resources removed from Git | Production — keeps cluster clean |
| `automated.prune: false` | Manual `kubectl delete` required | Vault — never auto-delete data |
| `automated.selfHeal: true` | Revert manual `kubectl edit` changes back to Git | Production — Git is truth |
| `automated.selfHeal: false` | Allow manual overrides to persist | Dev clusters |
| `syncOptions: CreateNamespace=true` | Create destination ns if missing | Always |
| `syncOptions: ServerSideApply=true` | Server-Side Apply | Large CRDs (avoid "annotation too long") |
| `syncOptions: Replace=true` | `kubectl replace` instead of `apply` | Rare; when patches fail |
| `syncOptions: PrunePropagationPolicy=foreground` | Wait for child resources before deleting parent | StatefulSets, Jobs |

### App-of-Apps Pattern

Manage many ArgoCD Applications via... another ArgoCD Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/akhil27051999/Flask-REST-API.git
    targetRevision: main
    path: argocd                       # ← folder of Application YAMLs
    directory:
      recurse: false
      exclude: root-app.yaml           # ← prevent self-management loop
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Apply once:**
```bash
kubectl apply -f argocd/root-app.yaml
```

ArgoCD now manages itself + all child apps. This is **how you bootstrap an entire cluster from a single command**.

### Multi-Source Pattern (We Use This for Observability)

For apps where you want to use an upstream Helm chart but customize via your repo's values.yaml:

```yaml
spec:
  sources:
    - repoURL: https://prometheus-community.github.io/helm-charts
      chart: prometheus
      targetRevision: 25.27.0
      helm:
        valueFiles:
          - $values/helm/prometheus/values.yaml   # ← from second source
    - repoURL: https://github.com/akhil27051999/Flask-REST-API.git
      targetRevision: main
      ref: values                                  # ← named ref used above
```

This avoids vendoring upstream charts in your repo while keeping all customization in Git.

### Sync Waves (Ordering)

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"   # earlier than 0
```

Resources sync in wave order: -1 → 0 → 1 → 2. Use for dependencies (Vault before ESO before Flask).

### Health States

| State | Meaning |
|-------|---------|
| **Healthy** | All resources running as expected |
| **Progressing** | Rollout in progress |
| **Degraded** | Resource is unhealthy (CrashLoopBackOff, etc.) |
| **Suspended** | Manually paused |
| **Missing** | Resource defined in Git but not in cluster |

### Sync States

| State | Meaning |
|-------|---------|
| **Synced** | Cluster matches Git |
| **OutOfSync** | Drift detected (Git changed OR manual cluster change) |
| **Unknown** | ArgoCD can't determine |

### How ArgoCD Detects Changes

| Method | When |
|--------|------|
| **Polling** | Every 3 min by default — checks for new Git commits |
| **Webhook** | Configure GitHub/GitLab webhook → `argocd-server/api/webhook` for instant sync |
| **Manual** | `argocd app sync <name>` or UI button or `kubectl patch application` |

Force a sync via kubectl:
```bash
kubectl patch application flask-api -n argocd --type merge \
  -p '{"operation":{"sync":{"revision":"main"}}}'
```

---

## The CI → GitOps → Deploy Loop

This is the full lifecycle from code change to running pod:

```
1. Developer pushes app/* code → main branch
2. GitHub Actions (Module 3):
   - build job: tests + builds image + pushes to DockerHub
   - update-helm job: sed updates helm/application/values.yaml tag → commits to main
3. ArgoCD detects values.yaml diff on main (within 3 min, or instant via webhook)
4. ArgoCD renders the Helm chart with new image tag
5. ArgoCD applies new manifests to K8s
6. Kubernetes rolling update — old pods drained, new pods come up
7. ArgoCD shows Synced + Healthy
```

This is **pull-based GitOps** — CI never touches the cluster directly. Git is the contract.

### Tested in this project

We bumped Flask replicas from 2 → 3 in `helm/application/values.yaml`, pushed, and a third pod appeared in ~3 seconds (after triggering manual sync to skip the 3-min poll).

---

## Commands Reference

### Helm

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Add a repo | `helm repo add bitnami https://charts.bitnami.com/bitnami` | Register external chart source |
| 2 | Update repos | `helm repo update` | Fetch latest chart versions |
| 3 | Search a chart | `helm search repo postgres` | Find available charts |
| 4 | Show default values | `helm show values bitnami/postgresql` | See what's configurable |
| 5 | Render template (no install) | `helm template student-api helm/application` | Preview rendered YAML |
| 6 | Install a chart | `helm install student-api helm/application -n student-api --create-namespace` | Deploy |
| 7 | Upgrade | `helm upgrade student-api helm/application -n student-api` | Apply changes |
| 8 | Idempotent install/upgrade | `helm upgrade --install student-api helm/application -n student-api` | Use in CI |
| 9 | List releases | `helm list -n student-api` (or `-A`) | See what's installed |
| 10 | Show release history | `helm history student-api -n student-api` | All revisions |
| 11 | Rollback | `helm rollback student-api 1 -n student-api` | Revert to revision 1 |
| 12 | Show current values | `helm get values student-api -n student-api` | See active config |
| 13 | Show rendered manifest | `helm get manifest student-api -n student-api` | What's actually in cluster |
| 14 | Lint | `helm lint helm/application` | Catch syntax errors |
| 15 | Test | `helm test student-api -n student-api` | Run hook-marked test pods |
| 16 | Uninstall | `helm uninstall student-api -n student-api` | Remove all resources |
| 17 | Package chart | `helm package helm/application` | Create `.tgz` for distribution |
| 18 | Pull from a repo | `helm pull bitnami/postgresql` | Download tarball |

### ArgoCD (kubectl)

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Get all apps | `kubectl get applications -n argocd` | Status overview |
| 2 | Describe app | `kubectl describe application <name> -n argocd` | Sync state, events, conditions |
| 3 | Force sync | `kubectl patch application <name> -n argocd --type merge -p '{"operation":{"sync":{"revision":"main"}}}'` | Skip 3-min poll |
| 4 | Force replace sync | `kubectl patch application ... -p '{"operation":{"sync":{"revision":"main","syncStrategy":{"hook":{},"apply":{"force":true}}}}}'` | When normal sync fails |
| 5 | Get admin password | `kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' \| base64 -d` | Initial login |
| 6 | Port-forward UI | `kubectl port-forward svc/argocd-server -n argocd 8081:443` | Access UI at https://localhost:8081 |

### ArgoCD CLI (`argocd` binary)

```bash
# Login
argocd login localhost:8081 --username admin --password <pwd>

# List apps
argocd app list

# Get app details
argocd app get student-api

# Sync an app
argocd app sync student-api

# Show diff between Git and cluster
argocd app diff student-api

# Rollback to previous revision
argocd app rollback student-api

# Set parameter (override values temporarily)
argocd app set student-api -p app.image.tag=v2

# Delete app
argocd app delete student-api
```

---

## Troubleshooting

### Issues We Hit in This Session

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | ArgoCD app stuck `OutOfSync, Missing` | CRD not installed (e.g., for ExternalSecret) | Install CRDs separately: `kubectl apply -f <crd-bundle.yaml>` |
| 2 | `Version "v1" of external-secrets.io/ClusterSecretStore not installed` | Chart's apiVersion mismatches installed CRD versions | Update chart templates to match installed CRD version |
| 3 | Sync fails: namespace not found | Destination namespace doesn't exist and `CreateNamespace=true` not set | Add `syncOptions: [CreateNamespace=true]` to the Application spec |
| 4 | "Resource already exists" sync error | Resource was created outside ArgoCD (kubectl/helm) | Delete the orphan resource OR add Helm/ArgoCD ownership labels/annotations |
| 5 | Two ESO operators running | Bundled operator in chart + upstream Helm install both deployed | Pick one; uninstall the other |
| 6 | App shows `Synced` but pod has `CreateContainerConfigError` | Missing dependent Secret (e.g., `postgres-secret` not yet synced from Vault) | Verify ESO has authenticated to Vault and synced the secret |
| 7 | `port-forward: connection refused: 127.0.0.1:5000` | Gunicorn binds to 127.0.0.1 inside container | Set `GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000` in deployment env |
| 8 | ESO `OutOfSync` after operator uninstall | CRDs were removed with operator | Reinstall CRDs from upstream chart (`--set crds.keep=true` to prevent recurrence) |
| 9 | Sync stops retrying after 5 attempts | ArgoCD has retry limit | Fix root cause, then `kubectl patch application <name>` to retry |
| 10 | `helm install` from CLI fails: namespace not found | Namespace doesn't exist | Add `--create-namespace` flag |
| 11 | Helm upgrade succeeds but pods don't restart | Rolled out config, but pod template didn't change (e.g., ConfigMap edit) | Use `kubectl rollout restart deploy/<name>` OR add a `checksum/config` annotation |
| 12 | `helm template` output doesn't match `helm install` | `--dry-run` runs admission webhooks too | Use `--dry-run=server` for full validation |
| 13 | Rendered manifest has wrong indentation | `nindent` vs `indent` confusion | `nindent N` adds a leading newline; `indent N` does not. Use `nindent` after `:` |
| 14 | `Error: rendered manifests contain a resource that already exists` | Another release/manual create is using the resource name | Delete conflict OR rename resource OR add `helm.sh/resource-policy: keep` |

### Sync Status Debug Sequence

```bash
# 1. Get high-level status
kubectl get applications -n argocd

# 2. Detailed status of one app
kubectl describe application <name> -n argocd

# 3. Get specific resource statuses
kubectl get application <name> -n argocd -o json | \
  jq '.status.resources[] | select(.status != "Synced")'

# 4. Get error messages
kubectl get application <name> -n argocd -o json | \
  jq '.status.conditions, .status.operationState.message'

# 5. Force a manual sync
kubectl patch application <name> -n argocd --type merge \
  -p '{"operation":{"sync":{"revision":"main"}}}'

# 6. Check argocd controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50
```

---

## Interview Q&A

### GitOps Concepts

| Q | A |
|---|---|
| **What is GitOps?** | Operational practice where Git is the single source of truth for both app code AND deployment state. Changes happen via PRs; a controller (ArgoCD/Flux) reconciles cluster to match. |
| **Push vs Pull-based CD?** | Push: CI applies to cluster (CI needs creds). Pull: cluster pulls from Git (no creds in CI, continuous reconciliation, drift detection). |
| **Why not just `kubectl apply` from CI?** | No drift detection, no rollback via git, CI needs cluster creds (security risk), no continuous reconciliation. Manual changes to cluster are silently lost. |
| **What are GitOps's 4 principles?** | (1) Declarative — state described as code. (2) Versioned — stored in Git. (3) Pulled — automated agent applies. (4) Continuously reconciled — drift detected and corrected. |

### Helm

| Q | A |
|---|---|
| **What's a Helm chart?** | A package of K8s YAML templates with values, hooks, dependencies. Templates use Go template syntax. |
| **Helm 2 vs Helm 3?** | Helm 3 removed Tiller (in-cluster server). Uses kubeconfig directly. Better security, simpler. |
| **Where does Helm store releases?** | As K8s Secrets (default) in the release namespace, type `helm.sh/release.v1`. Each revision = one secret. |
| **How does `helm rollback` work?** | Reads the previous revision's secret (which has the rendered manifests + values), applies it. K8s does the actual rollout. |
| **What's a hook?** | A K8s resource (usually Job) annotated with `helm.sh/hook: pre-install` etc. Runs at lifecycle points. |
| **`helm template` vs `helm install --dry-run`?** | `template` = client-side render only. `--dry-run` = render + send to API server for validation (catches admission webhook errors). |
| **How to override values?** | `--set key=val`, `-f values.yaml`, `--values values.yaml`. Later overrides earlier. |
| **How to use a value from a secret in templates?** | Don't bake secrets in values. Use `lookup` function (Helm 3.1+) or external secret operator. |
| **How does dependency management work?** | `Chart.yaml` declares dependencies; `helm dependency update` downloads them into `charts/`. They render as part of the parent. |
| **What's `_helpers.tpl`?** | Files starting with `_` aren't rendered as manifests — they're partials (named templates). Use `define`/`include`. |
| **What's the difference between `include` and `template`?** | Both invoke a named template. `include` returns the rendered string (pipeable). `template` is an action — can't pipe to functions like `nindent`. Always use `include` in production. |

### ArgoCD

| Q | A |
|---|---|
| **What is ArgoCD?** | A K8s controller implementing GitOps. Watches Git, renders manifests, applies to cluster. UI + CLI + REST API for human/automation interaction. |
| **What's an Application in ArgoCD?** | A CRD that says "deploy what's at this Git path to this cluster destination." Argo's unit of GitOps. |
| **What's the App-of-Apps pattern?** | An ArgoCD Application whose source folder contains other Application manifests. Lets you bootstrap an entire cluster from one root app. |
| **What's `selfHeal`?** | If someone manually `kubectl edit`s a resource, ArgoCD reverts it back to Git state. Enforces Git as source of truth. |
| **What's `prune`?** | When a resource is removed from Git, ArgoCD deletes it from the cluster. Without prune, deleted resources linger. |
| **What's a sync wave?** | Annotation `argocd.argoproj.io/sync-wave: "-1"` controls order within a sync. Lower = earlier. Use for dependencies. |
| **How to handle secrets in ArgoCD?** | Never plaintext in Git. Use Vault + ESO (our approach), sealed-secrets (encrypted in Git), or SOPS. |
| **What's an `AppProject`?** | A grouping of Applications with shared restrictions (allowed Git repos, allowed destinations, allowed cluster resources). Used for multi-tenancy / RBAC. |
| **How does ArgoCD do RBAC?** | RBAC config maps role permissions (read/write/sync) to OIDC groups. Per-project + per-app permissions. |
| **What's `ApplicationSet`?** | A higher-level CRD that generates multiple Applications dynamically (e.g., "for each cluster in our fleet, create an Application"). |
| **How do you do canary or blue/green with ArgoCD?** | Use `Argo Rollouts` CRD — replaces Deployment with Rollout that supports canary, blue/green, traffic shaping. ArgoCD treats Rollouts as managed resources. |
| **How do you do rollbacks in GitOps?** | `git revert <commit>` — ArgoCD applies the reverted state. OR use ArgoCD UI/CLI to roll back to a prior synced revision. |
| **What if ArgoCD itself is broken?** | Bootstrap: `helm install argocd ...` then `kubectl apply -f root-app.yaml`. Everything else self-recovers from Git. |
| **Webhooks vs polling?** | Default = 3-min poll. For instant sync, configure GitHub/GitLab webhook → ArgoCD `/api/webhook`. |
| **Multi-cluster ArgoCD?** | One ArgoCD instance can manage many clusters by registering them as targets (`argocd cluster add`). Common in production. |

### Combined GitOps Q&A

| Q | A |
|---|---|
| **Walk me through your full CI → CD flow.** | Code push → GHA tests + builds image + pushes to DockerHub + sed-updates `helm/application/values.yaml` tag, commits to main → ArgoCD detects values.yaml change → renders Helm chart → applies new manifests → K8s rolling update. |
| **How do you handle multi-environment (dev/staging/prod)?** | Branch-based: dev branch → dev cluster; OR directory-based: `helm/application/values-dev.yaml`, `values-prod.yaml` referenced by separate ArgoCD apps; OR cluster-based with ApplicationSet. |
| **How do you prevent accidental destructive changes?** | Branch protection (require reviews); ArgoCD AppProject restrictions; Sentinel/OPA policies in CI; manual approval gates for prod via Application sync windows. |
| **What's the worst that can happen with `selfHeal: true`?** | Manual emergency fixes get reverted within minutes. Fix: temporarily disable selfHeal during incidents, OR make the fix in Git first. |
| **How do you debug a broken sync?** | `kubectl describe application <name> -n argocd` for events, `argocd app diff` to see what's different, check controller logs. |
| **How do you handle CRD ordering with operators?** | Sync waves: install operator first (wave -1), then CRs that use the operator's CRDs (wave 0). |
| **How do you do disaster recovery for the cluster?** | Bootstrap K8s (Terraform), install ArgoCD (Helm), apply root app, ArgoCD recreates everything from Git. Time: 10-30 min vs hours/days for manual. |

---

## STAR Stories

### Story 1: "Tell me about implementing GitOps in a team."

**Situation:** Team was deploying via `kubectl apply` from each developer's laptop. Drift was constant — production had configurations no one remembered making.

**Task:** Move to GitOps without disrupting active development.

**Action:**
1. Inventoried current cluster state — exported all manifests with `kubectl get all -A -o yaml > current-state.yaml`.
2. Wrote Helm charts for each service. Used `helm template` to verify rendered YAML matched cluster state.
3. Installed ArgoCD via Helm in a non-prod cluster first.
4. Created an ArgoCD Application for one non-critical service. Watched sync, verified it didn't change anything (already in sync).
5. Migrated services one-by-one. For each: added `app.kubernetes.io/managed-by: Helm` and `meta.helm.sh/release-name` annotations to existing resources so Helm could "adopt" them without recreating.
6. Once all services were ArgoCD-managed, **revoked direct cluster access** for developers; only ArgoCD could write to cluster.
7. Documented the new flow: "Want to deploy? Push to Git. ArgoCD does the rest."

**Result:** Drift dropped to zero. Audit log = `git log`. New joiners onboarded faster (no need for kubeconfig). Average deployment time went from 15 min (manual) to 3 min (commit + ArgoCD sync).

**Takeaway:** Migrate gradually. Don't try to GitOps-ify everything at once. Adopt existing resources via labels/annotations rather than recreating.

---

### Story 2: "Tell me about a Helm release that went wrong."

**Situation:** Upgraded a Helm chart that referenced a ConfigMap. The Deployment template didn't change, but the ConfigMap did. After `helm upgrade`, pods were still using the old config.

**Task:** Force pods to re-read the new ConfigMap without manual `kubectl rollout restart`.

**Action:**
1. Recognized this as the classic "ConfigMap update doesn't restart pods" problem.
2. Added a `checksum/config` annotation to the Deployment's pod template:
   ```yaml
   spec:
     template:
       metadata:
         annotations:
           checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
   ```
3. Now any change to configmap.yaml changes the checksum → changes the pod template hash → triggers a rolling update.
4. Tested by changing a config value; pods rolled correctly.

**Result:** All ConfigMap changes now auto-trigger restarts. Documented as a chart pattern.

**Takeaway:** Helm/K8s don't auto-restart pods on ConfigMap/Secret changes — pod template must change for the Deployment controller to roll. Checksum annotation is the standard fix.

---

### Story 3: "Tell me about an ArgoCD sync that wouldn't succeed."

**Situation:** Deployed our External Secrets Operator app via ArgoCD. The Application showed `OutOfSync, Missing` and refused to retry. Logs said `no matches for kind "ExternalSecret" in version "external-secrets.io/v1beta1"`.

**Task:** Figure out why CRDs weren't matching.

**Action:**
1. Verified CRDs were installed: `kubectl get crd | grep external-secrets`.
2. Checked installed versions: `kubectl get crd externalsecrets.external-secrets.io -o jsonpath='{.spec.versions[*].name}'` — showed `v1alpha1 v1beta1`.
3. But our chart used `apiVersion: external-secrets.io/v1` — that version wasn't installed!
4. Two options: (a) install newer CRDs that have v1, or (b) update chart to use v1beta1.
5. Chose (b) — minimal change, matches what's installed.
6. After fix, sync succeeded.

**Result:** ArgoCD reconciled successfully. Documented the lesson: "When CRD apiVersion mismatches, check installed versions vs chart-required versions."

**Takeaway:** ArgoCD sync errors often boil down to CRD version mismatches. Always verify `kubectl get crd <name> -o jsonpath='{.spec.versions[*].name}'` matches what your chart uses.

---

### Story 4: "Tell me about a time the ArgoCD self-heal saved you."

**Situation:** A teammate ran `kubectl edit deployment` directly to "quickly" change a Flask replica count for debugging. Forgot to revert.

**Task:** Catch the drift before it caused issues in the next planned deployment.

**Action:**
1. ArgoCD's `selfHeal: true` was enabled — within ~3 minutes, ArgoCD reverted the manual change back to the Git-defined replica count.
2. We saw the activity in the ArgoCD UI: "OutOfSync detected → auto-sync applied → Synced."
3. Investigated the drift event in the ArgoCD audit log — found the `kubectl edit` user.
4. Conversation with the teammate: explained the GitOps boundary. They submitted a real PR for any future config changes.

**Result:** Drift caught and reverted automatically. Used as a teaching moment to reinforce the "no kubectl edit" policy.

**Takeaway:** SelfHeal is an enforcement tool, not just a convenience. It prevents "I'll just temporarily..." from becoming permanent untracked drift.

---

## Production Hardening

### Helm

| Area | Current | Production |
|------|---------|-----------|
| **Chart versioning** | Single chart, single version | Versioned charts; semver discipline; Chart.yaml `version` bumped per change |
| **Chart repository** | Local | Private chart repo (Harbor, ChartMuseum, OCI registry) |
| **Lint in CI** | None | `helm lint` + `helm template ... \| kubeconform -strict` |
| **Test pods** | None | Use `helm.sh/hook: test` annotated pods that verify deploy |
| **Sub-charts** | None | Use community charts (bitnami/postgresql, etc.) over rolling your own |
| **Secrets** | Inline | Sealed-secrets / SOPS / external secret operator |
| **Multi-env** | Single values.yaml | values-{dev,staging,prod}.yaml or HelmFile |
| **Diff tooling** | None | `helm diff` plugin to preview upgrade changes |

### ArgoCD

| Area | Current | Production |
|------|---------|-----------|
| **Auth** | admin/initial-password | OIDC SSO (Google/Okta/GitHub) |
| **RBAC** | Default (admin everything) | AppProject restrictions per team; least-privilege roles |
| **Sync windows** | None | Block syncs during business hours for prod (`spec.syncWindows`) |
| **Notifications** | None | argocd-notifications → Slack on sync failures, PagerDuty for prod |
| **Backups** | None | Backup ArgoCD Applications (they're just K8s resources) via Velero |
| **HA** | Single replica | Multi-replica controller, redis-ha, server replicas behind LB |
| **Image updater** | sed in CI | argocd-image-updater (auto-bumps on new image tags) |
| **Webhooks** | 3-min poll | GitHub webhook → ArgoCD `/api/webhook` for instant sync |
| **Self-management** | One-shot install | ArgoCD manages itself via an Application pointing to its own chart |

### GitOps as a Whole

| Area | Production |
|------|-----------|
| **Branch protection** | Require reviews + CI passing for main |
| **Policy as code** | OPA Gatekeeper / Kyverno admission rules |
| **Drift alerting** | `argocd app list -o json \| jq` cron → alert on OutOfSync apps |
| **Multi-cluster** | One ArgoCD instance per region, OR a control-plane ArgoCD that syncs to many cluster |
| **Disaster recovery** | Bootstrap script: install K8s → install ArgoCD → apply root app. RTO < 30 min. |
| **Audit** | All changes via Git (audit by `git log`); ArgoCD's own audit log shipped to SIEM |

---

## Cloud Mapping

### Helm Equivalents

| Helm | AWS-Native | GCP | Other |
|------|-----------|-----|-------|
| Helm chart | CloudFormation StackSets | Deployment Manager | Terraform module (different paradigm) |
| Chart repository | ECR (OCI helm) | Artifact Registry | ChartMuseum, Harbor |
| Hooks | Custom Resources | Custom Resources | Argo Workflows |

### GitOps Tools

| Tool | Notes |
|------|-------|
| **ArgoCD** | UI-driven, CRD-based, multi-tenant, app-of-apps. What we use. |
| **Flux** | CLI-driven, more lightweight, better image automation built-in |
| **Spinnaker** | Heavier, multi-cloud, pipeline-based — not strictly GitOps |
| **Jenkins X** | GitOps + opinionated CI/CD on K8s |

### App-of-Apps Equivalents Outside K8s

| Concept | Equivalent |
|---------|-----------|
| App-of-Apps | Terraform root module composing other modules |
| ArgoCD Application | Kustomize overlay + git workflow |
| Sync wave | Terraform `depends_on` |

---

## Reference Links (Internal)

- Helm charts: [helm/](../helm/)
  - Application chart: [helm/application/](../helm/application/)
  - Vault chart: [helm/vault/](../helm/vault/)
  - Database chart: [helm/database/](../helm/database/)
  - External-secrets chart: [helm/external-secrets/](../helm/external-secrets/)
- ArgoCD apps: [argocd/](../argocd/)
  - Root app: [argocd/root-app.yaml](../argocd/root-app.yaml)
  - Vault: [argocd/vault.yaml](../argocd/vault.yaml)
  - Database: [argocd/database.yaml](../argocd/database.yaml)
  - Application: [argocd/application.yaml](../argocd/application.yaml)
  - External-secrets: [argocd/external-secrets.yaml](../argocd/external-secrets.yaml)
