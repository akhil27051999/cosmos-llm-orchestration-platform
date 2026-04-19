# Module 5: Kubernetes Orchestration

> **Goal:** Deploy the entire stack — Vault, External Secrets Operator, Postgres, Flask — onto a 3-node minikube cluster that mimics a production multi-AZ topology.

> **Why this matters:** Kubernetes is the de-facto orchestrator for cloud-native workloads. For a 3-5 yr SRE/DevOps role, you must understand the **why** behind every K8s primitive — networking, storage, scheduling, secrets, rollouts. This is the single longest module because K8s is the single most-asked topic in interviews.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Why 3 Nodes with Labels](#why-3-nodes-with-labels)
3. [Cluster Setup](#cluster-setup)
4. [Vault Deployment](#vault-deployment)
5. [External Secrets Operator (ESO)](#external-secrets-operator-eso)
6. [Database (Postgres)](#database-postgres)
7. [Application (Flask)](#application-flask)
8. [Deep Concepts](#deep-concepts)
   - [Networking & CoreDNS](#networking--coredns)
   - [Storage — PV, PVC, StorageClass](#storage--pv-pvc-storageclass)
   - [Workloads — Deployment vs StatefulSet vs DaemonSet](#workloads--deployment-vs-statefulset-vs-daemonset)
   - [Probes — Liveness, Readiness, Startup](#probes--liveness-readiness-startup)
   - [Rollouts & Rollbacks](#rollouts--rollbacks)
   - [Autoscaling — HPA, VPA, Cluster Autoscaler](#autoscaling--hpa-vpa-cluster-autoscaler)
   - [NetworkPolicies](#networkpolicies)
   - [RBAC](#rbac)
   - [Operators & CRDs](#operators--crds)
9. [Commands Reference](#commands-reference)
10. [Troubleshooting](#troubleshooting)
11. [Interview Q&A](#interview-qa)
12. [STAR Stories](#star-stories)
13. [Production Hardening](#production-hardening)
14. [Cloud Mapping](#cloud-mapping)

---

## Architecture

```
                        Three-Node Minikube Cluster
                        (mimics multi-AZ K8s in cloud)

┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  Node: minikube           Node: minikube-m02       Node: minikube-m03 │
│  Label: type=application  Label: type=database     Label: type=        │
│  (Control plane)          (Worker)                  dependent_services │
│                                                     (Worker)           │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐ │
│  │ flask-api        │    │ postgres         │    │ vault           │ │
│  │ (3 replicas)     │    │ (single replica) │    │ (single replica)│ │
│  │ student-api ns   │    │ student-api ns   │    │ vault ns        │ │
│  └──────────────────┘    └──────────────────┘    │                 │ │
│                                                   │ external-secrets│ │
│                                                   │ -operator       │ │
│                                                   │ external-secrets│ │
│                                                   │ ns              │ │
│                                                   └─────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘

Data flow:
  flask-api ◄── postgres-secret (synced from Vault by ESO)
  flask-api ──► postgres (over cluster DNS)
  ESO ──► vault-service (over cluster DNS, cross-namespace)
```

**Workload-to-node placement** (via `nodeSelector`):

| Pod | Lands on | Why |
|-----|----------|-----|
| Flask API | `type=application` (minikube) | App workloads isolated to "app tier" |
| Postgres | `type=database` (minikube-m02) | DB on dedicated node — no noisy neighbors |
| Vault, ESO | `type=dependent_services` (minikube-m03) | Infra/security tools separate from app & DB |

---

## Why 3 Nodes with Labels

This mimics a real production setup where:
- **Application nodes** auto-scale based on traffic
- **Database nodes** are large, stable, and rarely restart (different SLAs)
- **Dependent services** (Vault, monitoring, secrets) run on infra-tier nodes

Labels + nodeSelectors enforce the placement. In cloud, you'd use **node groups** (EKS) or **node pools** (GKE) with the same labels.

---

## Cluster Setup

### Prerequisites

| Tool | Install (macOS) | Why |
|------|-----------------|-----|
| `minikube` | `brew install minikube` | Local K8s cluster |
| `kubectl` | `brew install kubectl` | K8s CLI |
| `helm` | `brew install helm` | Package manager (used in Module 6) |
| `k9s` (optional) | `brew install k9s` | Terminal UI for K8s |

### Create the 3-node cluster

```bash
minikube start --nodes=3 --driver=docker --cpus=2 --memory=2048
kubectl get nodes
```

You should see:
```
NAME           STATUS   ROLES           AGE   VERSION
minikube       Ready    control-plane   1m    v1.35.1
minikube-m02   Ready    <none>          50s   v1.35.1
minikube-m03   Ready    <none>          40s   v1.35.1
```

### Label the nodes

```bash
kubectl label node minikube       type=application --overwrite
kubectl label node minikube-m02   type=database --overwrite
kubectl label node minikube-m03   type=dependent_services --overwrite

kubectl get nodes --show-labels | grep type=
```

---

## Vault Deployment

### What is Vault?

A secrets management server. Provides:
- **Encryption-at-rest** for secrets (vs plaintext base64 in K8s Secrets)
- **Dynamic secrets** (generates DB creds on-demand)
- **Audit log** of every secret access
- **Fine-grained policies** (read-only, time-bound, scoped)

### Deploy

```bash
kubectl apply -f k8s/vault.yaml
kubectl wait --for=condition=ready pod -l app=vault -n vault --timeout=180s
```

The pod runs but reports **NotReady** because Vault always starts **sealed**.

### Initialize

```bash
kubectl exec -n vault -it deployment/vault -- vault operator init
```

Output:
```
Unseal Key 1: ...
Unseal Key 2: ...
Unseal Key 3: ...
Unseal Key 4: ...
Unseal Key 5: ...
Initial Root Token: hvs.xxxxxxxxxx
```

**SAVE THESE.** Without 3 of 5 unseal keys, the data in Vault is permanently lost. Vault uses **Shamir's Secret Sharing** — split into 5, need 3 to reconstruct.

### Unseal (3 of 5 keys)

```bash
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key1>
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key2>
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key3>

kubectl exec -n vault -it deployment/vault -- vault status
# Should show: Sealed: false
```

### Login & Store Secrets

```bash
kubectl exec -n vault -it deployment/vault -- sh -c '
vault login <root-token> &&
vault secrets enable -path=secret kv-v2 &&
vault kv put secret/studentdb \
  POSTGRES_USER=postgres \
  POSTGRES_PASSWORD=postgres123 \
  POSTGRES_DB=studentdb
'
```

**Why KV-v2?** Versioned secrets — every update creates a new version, can roll back, soft-delete with `vault kv delete` (data still recoverable).

### Why Vault Restarts Mean Re-Unsealing

Vault stores secrets encrypted with a **master key** held in memory (never on disk). On restart, the master key is gone — must reconstruct from unseal keys. **Production:** auto-unseal with cloud KMS (AWS KMS / GCP KMS / Azure Key Vault) so this is automatic.

---

## External Secrets Operator (ESO)

### What problem does it solve?

K8s native Secrets are:
- **Base64-encoded, not encrypted** (visible to anyone with `kubectl get secret`)
- **Stored in etcd** (compromise of etcd = all secrets exposed)
- **No rotation** built-in
- **No audit trail** of access

Vault solves all that — but apps would need a **Vault SDK** to fetch secrets. ESO bridges the gap: apps still use native K8s Secrets, ESO syncs them from Vault.

### Architecture

```
Vault ──[reads]── ESO Operator ──[creates/updates]──► K8s Secret
                                                           │
                                                           │ secretKeyRef
                                                           ▼
                                                       Pod (env vars)
```

Pod sees a normal K8s Secret. ESO is the watcher that keeps it in sync.

### Install ESO

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets external-secrets/external-secrets \
  -n external-secrets --create-namespace \
  --set installCRDs=true
```

Three pods come up:
- `external-secrets-operator` — the controller
- `external-secrets-cert-controller` — manages webhook certs
- `external-secrets-webhook` — admission webhook for CRD validation

### Create the Vault Token Secret (Out-of-Band)

ESO needs a Vault token to authenticate. We can't put it in Git, so create manually:

```bash
kubectl create secret generic vault-token \
  --from-literal=token=<root-token> \
  -n external-secrets
```

### Define ClusterSecretStore + ExternalSecret

**[k8s/external-secrets-store.yaml](../k8s/external-secrets-store.yaml):**

```yaml
apiVersion: external-secrets.io/v1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "http://vault-service.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        tokenSecretRef:
          name: vault-token
          key: token
          namespace: external-secrets
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: studentdb-secrets
  namespace: student-api
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: postgres-secret
    creationPolicy: Owner
  data:
    - secretKey: POSTGRES_USER
      remoteRef: { key: studentdb, property: POSTGRES_USER }
    - secretKey: POSTGRES_PASSWORD
      remoteRef: { key: studentdb, property: POSTGRES_PASSWORD }
```

**Apply:**
```bash
kubectl apply -f k8s/external-secrets-store.yaml
```

ESO controller reads `ExternalSecret`, queries Vault, creates a K8s Secret named `postgres-secret` in `student-api` namespace.

### Force Sync (Skip 1h Refresh)

```bash
kubectl annotate externalsecret studentdb-secrets -n student-api \
  force-sync=$(date +%s) --overwrite
```

---

## Database (Postgres)

**[k8s/database.yaml](../k8s/database.yaml)** — single-replica Deployment with PVC.

Key elements:
- **PVC `postgres-pvc`** — 1Gi from `standard` StorageClass
- **`nodeSelector: type=database`** — pinned to minikube-m02
- **Env from `postgres-secret`** (synced by ESO)
- **Env from `postgres-config` ConfigMap** for non-secret config (host, port, db name)

```yaml
spec:
  template:
    spec:
      nodeSelector:
        type: database
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef: { name: postgres-secret, key: POSTGRES_USER }
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef: { name: postgres-secret, key: POSTGRES_PASSWORD }
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
```

**Why Deployment, not StatefulSet?** For learning — Deployment is simpler. Production should use **StatefulSet** for stable identity, ordered startup, and per-pod PVCs (covered later).

---

## Application (Flask)

**[k8s/application.yaml](../k8s/application.yaml)** — 2-replica Deployment with init container for migrations.

Key elements:

```yaml
spec:
  replicas: 2
  template:
    spec:
      nodeSelector:
        type: application
      initContainers:                                     # ← migrations
      - name: db-migrations
        image: akhilthyadi/flask-app:7.0.0
        command: ["sh", "-c", "until pg_isready ...; do sleep 2; done; flask db upgrade"]
      containers:
      - name: flask-api
        image: akhilthyadi/flask-app:7.0.0
        ports: [{ containerPort: 5000 }]
        env:
        - name: GUNICORN_CMD_ARGS
          value: "--bind=0.0.0.0:5000 --workers=2"        # ← critical!
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef: { name: postgres-secret, key: POSTGRES_USER }
```

**Init container pattern:**
1. Waits for Postgres to be ready (`pg_isready` loop)
2. Runs `flask db upgrade` to apply migrations
3. Exits cleanly → main `flask-api` container starts

This guarantees the schema exists before the app accepts traffic.

**`GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000`** — the most important env var. Without it, Gunicorn binds to `127.0.0.1` (loopback), and the K8s Service can't route traffic to it.

---

## Deep Concepts

### Networking & CoreDNS

#### The 4 K8s Networking Problems

| Problem | Solution | Example |
|---------|----------|---------|
| Container ↔ container in same pod | Shared network namespace (`localhost`) | Init container + main container talk via `localhost` |
| Pod ↔ pod | CNI plugin (Kindnet, Calico, Cilium) — every pod gets unique IP | Flask pod (10.244.0.5) → Postgres pod (10.244.1.4) |
| Pod ↔ Service | kube-proxy + iptables/IPVS DNAT | Flask pod uses `postgres:5432` → kube-proxy DNATs to actual pod IP |
| External ↔ pod | NodePort / LoadBalancer / Ingress | NodePort exposes flask-api-service on each node's IP |

#### CoreDNS — The Answer to "How does service discovery work?"

CoreDNS runs as a Deployment in `kube-system`, exposed via a Service called `kube-dns` at IP `10.96.0.10`.

**`/etc/resolv.conf` injected into every pod by kubelet:**
```
nameserver 10.96.0.10
search student-api.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```

**The query flow when Flask runs `psycopg2.connect("postgres")`:**

1. App resolves `postgres` via libc resolver
2. Resolver sees `ndots:5` — name has 0 dots, less than 5, so try search domains first:
   - `postgres.student-api.svc.cluster.local` → ✅ matches! Returns `10.96.121.45` (Service ClusterIP)
3. Pod opens TCP to `10.96.121.45:5432`
4. kube-proxy's iptables rule DNATs to actual pod IP `10.244.1.4:5432`
5. Connection established

**DNS naming convention:**
| Name | Resolves To | Used By |
|------|-------------|---------|
| `postgres` | postgres service in **same namespace** | Flask in `student-api` |
| `postgres.student-api` | postgres in `student-api` from any ns | Cross-namespace shortcut |
| `postgres.student-api.svc.cluster.local` | FQDN | Always works, used in cross-ns configs |
| `vault-service.vault.svc.cluster.local` | Vault service from another namespace | ESO config in our project |

#### Service Types

| Type | Reachability | Use Case | In This Project |
|------|--------------|----------|-----------------|
| **ClusterIP** (default) | Inside cluster only | Internal services | `postgres`, `vault-service` |
| **NodePort** | Each node's IP at port 30000–32767 | Quick external access | `flask-api-service` |
| **LoadBalancer** | Cloud-provisioned external LB | Production external | Would use in EKS for prod |
| **ExternalName** | DNS CNAME | Alias external SaaS | Not used |
| **Headless** (`clusterIP: None`) | DNS returns pod IPs directly | StatefulSets | Postgres StatefulSet would use |

#### kube-proxy Modes

| Mode | How It Works | Scale |
|------|--------------|-------|
| **iptables** (default) | Linear-rule iptables chains | Up to ~1000 services |
| **IPVS** | Kernel-level load balancing (hash table) | Tens of thousands of services |
| **userspace** | Old, slow, deprecated | Don't use |

---

### Storage — PV, PVC, StorageClass

| Object | Created By | Purpose |
|--------|-----------|---------|
| **PersistentVolume (PV)** | Cluster admin OR dynamic provisioner | Actual chunk of storage (NFS, EBS, hostpath) |
| **PersistentVolumeClaim (PVC)** | Developer / app | Request for storage with size + access mode |
| **StorageClass** | Cluster admin | Template for dynamically creating PVs |

#### Static vs Dynamic Provisioning

| Static | Dynamic |
|--------|---------|
| Admin pre-creates PVs | StorageClass auto-creates PVs when PVC is created |
| Manual, doesn't scale | Automated, common in cloud |
| Used in on-prem | Used everywhere now |

minikube has a default StorageClass `standard` (hostpath provisioner) — files end up at `/var/hostpath-provisioner/<ns>/<pvc-name>` on the node.

#### Access Modes

| Mode | Meaning | Use Case |
|------|---------|----------|
| **ReadWriteOnce (RWO)** | One node mounts RW | Postgres, Vault — single writer |
| **ReadWriteMany (RWX)** | Multiple nodes mount RW | Shared file storage (NFS, EFS) |
| **ReadOnlyMany (ROX)** | Multiple nodes mount RO | Static configs |
| **ReadWriteOncePod** | Only one POD mounts | Strict single-writer |

#### Reclaim Policies

| Policy | What Happens When PVC Deleted |
|--------|-------------------------------|
| **Retain** (default for static) | PV kept; data preserved; manual cleanup |
| **Delete** (default for dynamic) | PV + underlying storage deleted |
| **Recycle** (deprecated) | Data scrubbed, PV reused |

---

### Workloads — Deployment vs StatefulSet vs DaemonSet

| Aspect | Deployment | StatefulSet | DaemonSet |
|--------|-----------|-------------|-----------|
| **Pod naming** | Random (`flask-api-67769d47d5-2qq8s`) | Ordered (`postgres-0`, `postgres-1`) | One per node (`promtail-xyz`) |
| **Storage** | Shared PVC across replicas | Each pod gets own PVC via `volumeClaimTemplates` | Usually no PVC |
| **Use case** | Stateless apps (Flask) | Databases, queues, anything stateful | Per-node agents (logging, monitoring, CNI) |
| **Scaling** | Random order | Strict ordinal (0 → 1 → 2 to scale up; 2 → 1 → 0 to scale down) | Auto: one per node |
| **DNS** | Single ClusterIP via Service | Stable per-pod DNS via headless Service | Same as Deployment |

#### Why Postgres Should Be a StatefulSet (Production)

We used Deployment in this project for simplicity. Production reasons to use StatefulSet:
- **Stable identity** — pod-0 is always primary, can do replication setup
- **Per-pod PVC** — `volumeClaimTemplates` creates `data-postgres-0`, `data-postgres-1` separately
- **Ordered startup/teardown** — primary up first, then replicas
- **Stable DNS** — `postgres-0.postgres.student-api.svc.cluster.local`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres   # must reference a headless service
  replicas: 3
  volumeClaimTemplates:   # ← per-pod PVC
    - metadata: { name: data }
      spec:
        accessModes: [ReadWriteOnce]
        resources: { requests: { storage: 10Gi } }
```

#### Init Containers vs Sidecars

| Type | When | Lifecycle | Project Example |
|------|------|-----------|----------------|
| **Init container** | Before main container starts | Runs once, exits | `db-migrations` runs `flask db upgrade` before Flask starts |
| **Sidecar** | Alongside main container | Lives the lifetime of the pod | A log shipper next to Flask |

---

### Probes — Liveness, Readiness, Startup

Without proper probes, K8s routes traffic to pods that aren't ready yet → 5xx errors during deploys.

| Probe | Question Answered | Failure Action |
|-------|------------------|---------------|
| **livenessProbe** | "Is this pod alive?" | K8s **restarts** the pod |
| **readinessProbe** | "Can this pod accept traffic?" | K8s **removes** pod from Service endpoints |
| **startupProbe** | "Is the app done starting?" | Disables liveness until passes (for slow-starting apps) |

**Vault example:**
```yaml
readinessProbe:
  httpGet:
    path: /v1/sys/health
    port: 8200
  initialDelaySeconds: 10
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /v1/sys/health
    port: 8200
  initialDelaySeconds: 60
  periodSeconds: 30
```

This is why Vault shows `0/1` until unsealed — `/v1/sys/health` returns 503 when sealed → readiness fails → not "ready" → no traffic.

**Probe types:**
- `httpGet` — HTTP request, success on 2xx/3xx
- `tcpSocket` — TCP connect succeeds
- `exec` — Command exits 0
- `grpc` — gRPC health check

---

### Rollouts & Rollbacks

#### Hierarchy

```
Deployment
   ↓ creates and manages
ReplicaSet
   ↓ creates and manages
Pods
```

When you change the Deployment (image, env, etc.), it creates a **new ReplicaSet** and gradually scales it up while scaling old one down.

#### Strategies

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| **RollingUpdate** (default) | Gradually replaces old pods | Zero-downtime deployments |
| **Recreate** | Kills all old, then creates new | Apps that can't run two versions (schema change) |

#### RollingUpdate Tuning

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1          # extra pods allowed above desired
    maxUnavailable: 0    # no pods allowed unavailable
```

With 2 replicas, `maxSurge=1, maxUnavailable=0`:
1. Create 1 new pod → 3 pods (2 old + 1 new)
2. New pod ready → kill 1 old → 2 pods (1 old + 1 new)
3. Create 1 more new → 3 pods (1 old + 2 new)
4. New pod ready → kill last old → 2 pods (2 new)

**Zero downtime** if probes are correct.

#### Commands

```bash
kubectl rollout status deployment/flask-api -n student-api    # watch progress
kubectl rollout history deployment/flask-api -n student-api   # show revisions
kubectl rollout undo deployment/flask-api -n student-api      # roll back to previous
kubectl rollout undo deployment/flask-api --to-revision=2 -n student-api
kubectl rollout restart deployment/flask-api -n student-api   # force restart all pods
kubectl rollout pause deployment/flask-api -n student-api     # pause in-progress
kubectl rollout resume deployment/flask-api -n student-api
```

K8s keeps `revisionHistoryLimit` old ReplicaSets (default: 10) — rollback is just scaling old RS up + new RS down.

---

### Autoscaling — HPA, VPA, Cluster Autoscaler

Three layers of autoscaling:

| Tool | What It Scales | Trigger |
|------|---------------|---------|
| **HPA (Horizontal Pod Autoscaler)** | Number of pod replicas | CPU, memory, custom metrics |
| **VPA (Vertical Pod Autoscaler)** | Pod CPU/memory requests | Historical usage |
| **Cluster Autoscaler** | Number of nodes | Pending pods (can't schedule due to resources) |
| **KEDA** | Pods based on events | Queue depth, Kafka lag, Prometheus metrics |

#### HPA — Horizontal Pod Autoscaler

Scales `replicas` of a Deployment based on metrics. Most common usage: CPU%.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: flask-api
  namespace: student-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: flask-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70    # scale up when avg CPU > 70%
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # wait 5 min before scaling down (avoid flapping)
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100   # double pods at most per 60s
        periodSeconds: 60
```

**Prerequisites:**
- `metrics-server` installed (`minikube addons enable metrics-server`)
- Pod must have `resources.requests` defined (HPA uses % of requests)

**Apply:**
```bash
kubectl apply -f hpa.yaml
kubectl get hpa -n student-api -w
```

**Custom metrics HPA:** scale based on Prometheus metrics (`flask_http_request_total` rate) using `prometheus-adapter` or KEDA.

**HPA gotchas:**
| Gotcha | Fix |
|--------|-----|
| HPA scales to 0 then back, oscillating | Tune `stabilizationWindowSeconds` (default 300s for scale-down) |
| HPA never scales | metrics-server not installed; pod has no `resources.requests` |
| HPA scales too aggressively | Add `behavior.scaleUp.policies` with `periodSeconds` |
| HPA fights with `kubectl scale` | Don't manually scale a Deployment that has HPA |

#### VPA — Vertical Pod Autoscaler

Recommends (or auto-applies) better CPU/memory **requests** based on actual usage.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: flask-api
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: flask-api
  updatePolicy:
    updateMode: "Auto"   # or "Off" (recommend only), "Initial" (only on pod create)
  resourcePolicy:
    containerPolicies:
    - containerName: flask-api
      minAllowed: { cpu: 100m, memory: 128Mi }
      maxAllowed: { cpu: 1, memory: 1Gi }
```

**Modes:**
- `Off` — recommendations only (safest, see in `kubectl describe vpa`)
- `Initial` — set requests at pod creation
- `Auto` — restart pods to apply new requests (disruptive!)

**HPA + VPA together?** Not for the same metric. Use HPA on CPU + VPA in `Off` mode for memory recommendations.

#### Cluster Autoscaler

Scales the **number of nodes** in your cluster. Triggered when pods are `Pending` due to insufficient resources.

In cloud:
- AWS: `cluster-autoscaler` watches Auto Scaling Groups
- GCP/Azure: native managed cluster autoscaler

```yaml
# Annotations on the deployment to inform autoscaler
metadata:
  annotations:
    cluster-autoscaler.kubernetes.io/safe-to-evict: "false"   # data pods
```

#### KEDA — Event-Driven Autoscaling

For workloads driven by events (queues, Kafka, Prometheus), HPA on CPU isn't enough. KEDA provides 60+ "scalers":
- Scale based on Kafka lag
- Scale based on Redis queue length
- Scale based on Prometheus query result
- Scale to ZERO when no events (cost saver!)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
spec:
  scaleTargetRef:
    name: flask-api
  minReplicaCount: 0     # scale to zero!
  maxReplicaCount: 100
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.observability.svc:9090
      metricName: flask_request_rate
      threshold: '100'
      query: sum(rate(flask_http_request_total[1m]))
```

---

### NetworkPolicies

By default, **all pods can talk to all other pods**. NetworkPolicies are pod-level firewall rules.

⚠️ **Only enforced if your CNI supports it.** Calico, Cilium, Weave do. Kindnet (minikube default) does not — policies apply but are ignored.

**Default-deny (production foundation):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: student-api
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  # No rules = deny everything
```

**Allow Flask → Postgres:**
```yaml
spec:
  podSelector:
    matchLabels: { app: postgres }
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector: { matchLabels: { app: flask-api } }
    ports:
    - protocol: TCP
      port: 5432
```

**Critical gotcha — DNS:** if you apply default-deny egress, pods can't resolve DNS (can't reach CoreDNS). Always allow:

```yaml
egress:
- to:
  - namespaceSelector:
      matchLabels: { kubernetes.io/metadata.name: kube-system }
    podSelector:
      matchLabels: { k8s-app: kube-dns }
  ports:
  - protocol: UDP
    port: 53
  - protocol: TCP
    port: 53
```

---

### RBAC

| Object | Scope | Example |
|--------|-------|---------|
| **Role** | Namespace | "Read pods in student-api" |
| **ClusterRole** | Cluster-wide | "Read pods in any namespace" |
| **RoleBinding** | Bind Role to subject in a namespace | Grants developer the Role |
| **ClusterRoleBinding** | Bind ClusterRole cluster-wide | ESO has this to manage secrets across all namespaces |

In our project, **ESO ClusterRole** lets it read/write Secrets across all namespaces (it creates `postgres-secret` in `student-api`).

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: external-secrets-cluster-role
rules:
  - apiGroups: [""]
    resources: ["secrets", "namespaces", "events"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["external-secrets.io"]
    resources: ["secretstores", "clustersecretstores", "externalsecrets"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

---

### Operators & CRDs

#### What's an Operator?

An app that **operates** other apps. Encodes domain knowledge ("how to back up Postgres", "how to rotate secrets") as code.

**Pattern:** CRD (defines new resource type) + Custom Controller (watches for that resource and acts on it).

#### CRD vs CR vs Operator

| Term | Meaning |
|------|---------|
| **CRD** | The schema (`ExternalSecret`, `ClusterSecretStore`) |
| **CR** | An instance of that CRD (your `vault-backend` is a CR) |
| **Operator** | Controller that acts on CRs |

#### ESO as an Example

```
1. You apply: kind: ExternalSecret, name: studentdb-secrets, spec: {data: [...]}
2. ESO controller watches all ExternalSecret resources
3. Sees the new resource, parses spec
4. Calls Vault API: GET /v1/secret/data/studentdb (using vault-token)
5. Vault returns: { POSTGRES_USER: "postgres", POSTGRES_PASSWORD: "postgres123" }
6. Controller creates K8s Secret: name: postgres-secret, namespace: student-api
7. Controller updates ExternalSecret status to "Ready: True"
8. Every refreshInterval (1h), re-queries Vault and updates Secret if changed
```

#### Famous Operators

| Operator | Manages |
|----------|---------|
| **Prometheus Operator** | Prometheus + ServiceMonitor + Alertmanager |
| **cert-manager** | TLS certificates (Let's Encrypt) |
| **CloudNativePG** | Postgres HA clusters |
| **Strimzi** | Kafka clusters |
| **ArgoCD** | GitOps deployments |
| **Vault Operator** | Vault clusters |

---

## Commands Reference

### Cluster

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Start 3-node cluster | `minikube start --nodes=3 --driver=docker --cpus=2 --memory=2048` | Mimics multi-node production |
| 2 | Stop cluster | `minikube stop` | Pauses; data persists |
| 3 | Delete cluster | `minikube delete` | Wipes everything |
| 4 | Cluster info | `kubectl cluster-info` | Control plane URL |
| 5 | Get nodes | `kubectl get nodes -o wide` | IPs, status, version |
| 6 | Label node | `kubectl label node <node> type=app --overwrite` | For node selectors |
| 7 | Cordon (no new pods) | `kubectl cordon <node>` | Maintenance prep |
| 8 | Drain (move pods off) | `kubectl drain <node> --ignore-daemonsets` | Maintenance |
| 9 | Uncordon | `kubectl uncordon <node>` | Resume scheduling |

### Pods

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | List pods | `kubectl get pods -n <ns>` | Status overview |
| 2 | All namespaces | `kubectl get pods -A` | Cluster-wide |
| 3 | Wide info | `kubectl get pods -o wide` | IPs, nodes |
| 4 | Watch | `kubectl get pods -w` | Live updates |
| 5 | Describe | `kubectl describe pod <pod>` | Events, mounts, env |
| 6 | Logs | `kubectl logs <pod> -c <container>` | Multi-container |
| 7 | Logs previous instance | `kubectl logs <pod> --previous` | Crashed container |
| 8 | Tail logs | `kubectl logs -f <pod>` | Stream |
| 9 | Exec into pod | `kubectl exec -it <pod> -- sh` | Shell |
| 10 | Copy file in/out | `kubectl cp local.txt ns/<pod>:/path` | Bulk transfer |
| 11 | Port-forward | `kubectl port-forward svc/<svc> 8080:80` | Local access |
| 12 | Top (resource usage) | `kubectl top pods -n <ns>` | Requires metrics-server |
| 13 | Delete pod | `kubectl delete pod <pod>` | Forces restart (ReplicaSet recreates) |
| 14 | Force delete | `kubectl delete pod <pod> --force --grace-period=0` | When stuck Terminating |

### Workloads

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | List deployments | `kubectl get deploy -n <ns>` | Status |
| 2 | Scale | `kubectl scale deployment/flask-api --replicas=5 -n student-api` | Manual scale |
| 3 | Rollout status | `kubectl rollout status deployment/flask-api -n student-api` | Watch deploy |
| 4 | Rollout history | `kubectl rollout history deployment/flask-api -n student-api` | Revisions |
| 5 | Rollback | `kubectl rollout undo deployment/flask-api -n student-api` | Revert to previous |
| 6 | Restart all pods | `kubectl rollout restart deployment/flask-api -n student-api` | Re-read configmap/secret |
| 7 | Edit live | `kubectl edit deployment/flask-api -n student-api` | Quick edit (avoid in prod) |
| 8 | Apply YAML | `kubectl apply -f file.yaml` | Idempotent |
| 9 | Delete from YAML | `kubectl delete -f file.yaml` | Tear down |

### Networking

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | List services | `kubectl get svc -n <ns>` | Type, ClusterIP, ports |
| 2 | Describe service | `kubectl describe svc <svc>` | Endpoints, selector |
| 3 | List endpoints | `kubectl get endpoints <svc>` | Actual pod IPs backing the service |
| 4 | DNS test from pod | `kubectl exec -n <ns> <pod> -- nslookup postgres` | Verify CoreDNS |
| 5 | Ingress | `kubectl get ingress -A` | External routing |
| 6 | NetworkPolicies | `kubectl get netpol -A` | Pod firewall rules |

### Storage

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | List PVCs | `kubectl get pvc -n <ns>` | Storage requests |
| 2 | List PVs | `kubectl get pv` | Cluster-wide volumes |
| 3 | StorageClasses | `kubectl get sc` | Available provisioners |
| 4 | Describe PVC | `kubectl describe pvc <pvc>` | Bound PV, events |

### Debugging

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Events sorted | `kubectl get events --sort-by='.lastTimestamp' -A` | Recent activity |
| 2 | Describe everything | `kubectl describe <kind>/<name>` | Full state |
| 3 | API resources | `kubectl api-resources` | See all CRDs/types |
| 4 | Explain field | `kubectl explain pod.spec.containers` | Schema docs |
| 5 | Get all in namespace | `kubectl get all -n <ns>` | Quick overview |
| 6 | Dry run | `kubectl apply -f file.yaml --dry-run=client -o yaml` | Preview |

---

## Troubleshooting

### Issues We Hit in This Session

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | Vault pod 0/1 NotReady | Vault always starts sealed; readiness probe fails | Run `vault operator init` then `unseal` × 3 |
| 2 | ESO `OutOfSync, Missing` | CRDs not installed | `helm install external-secrets ... --set installCRDs=true` |
| 3 | ESO `InvalidProviderConfig: cannot get vault-token secret` | Secret not created in `external-secrets` namespace | `kubectl create secret generic vault-token --from-literal=token=<root-token> -n external-secrets` |
| 4 | `ClusterSecretStore is not ready` cached, ExternalSecret never re-tries | Default refresh is 1h | `kubectl annotate externalsecret <name> force-sync=$(date +%s) --overwrite` |
| 5 | `no matches for kind "ClusterSecretStore" in version "external-secrets.io/v1beta1"` | Chart uses different API version than installed CRDs | Check `kubectl get crd clustersecretstores.external-secrets.io -o jsonpath='{.spec.versions[*].name}'`; update YAML to match |
| 6 | Postgres / Vault PVC `permission denied` on minikube | hostpath provisioner doesn't honor `fsGroup` chown | SSH to node and chown: `minikube ssh -n minikube-m03 "sudo chown -R 10001:10001 /var/hostpath-provisioner/observability/storage-loki-0"` |
| 7 | `port-forward: connection refused: 127.0.0.1:5000` | Gunicorn binds to `127.0.0.1` (loopback) | Add `GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000` env var |
| 8 | Flask responds 404 for all /students | DB tables exist but empty | Run `python /api/app/seed.py` via `kubectl exec` |
| 9 | `seed.py: No such file or directory` in container | Older image; seed.py wasn't bundled | `kubectl cp` to copy in, or rebuild image with seed.py in `app/` |
| 10 | `minikube service` URL unreliable on Mac Docker driver | Tunnel disconnects | Use `kubectl port-forward` instead |
| 11 | Deleting `application.yaml` removed namespace | Namespace defined inline in the YAML | Recreate ns + redeploy postgres + ESO secret |
| 12 | Pod stuck `Pending` | Insufficient resources OR no node matches selector | `kubectl describe pod` → look at Events; verify node labels |
| 13 | `helm install` fails: namespace not found | Namespace doesn't exist | Add `--create-namespace` to helm install |
| 14 | Namespace stuck `Terminating` | Resource has finalizer waiting for a controller that's gone | `kubectl patch <resource> -p '{"metadata":{"finalizers":null}}' --type=merge` |
| 15 | Image `ImagePullBackOff` | Wrong tag or private registry without imagePullSecret | `kubectl describe pod` → events; verify tag exists |

### General Pod Lifecycle Debugging

| Symptom | Likely Cause | First Check |
|---------|-------------|-------------|
| `Pending` | No matching node, insufficient resources | `kubectl describe pod` → Events |
| `ContainerCreating` | Image pull, volume mount, secret/configmap missing | `kubectl describe pod` → Events |
| `CrashLoopBackOff` | App crashes on startup | `kubectl logs <pod> --previous` |
| `Error` | Pod terminated unsuccessfully | Logs + describe |
| `OOMKilled` | Hit memory limit | Increase `resources.limits.memory` |
| `Evicted` | Node out of disk/memory | `kubectl get events -A \| grep Evict` |
| `ImagePullBackOff` | Wrong image tag, private registry | Verify image exists; add `imagePullSecret` |
| `0/1 Running` (not Ready) | Readiness probe failing | `kubectl describe pod` → probe section; check `/health` endpoint |

### CrashLoopBackOff — Step-by-Step

```bash
# 1. Get the latest crash logs
kubectl logs <pod> --previous

# 2. Check init container logs separately
kubectl logs <pod> -c <init-container>

# 3. Inspect events
kubectl describe pod <pod> | grep -A 20 Events

# 4. Verify env vars are populated correctly
kubectl exec -it <pod> -- env | sort

# 5. Verify mounted secrets/configmaps
kubectl exec -it <pod> -- ls /etc/secrets

# 6. Run an interactive shell with the same image
kubectl run debug --rm -it --image=<your-image> -- sh
```

### Networking Debug

```bash
# Pod-to-pod from inside a debug pod
kubectl run debug --rm -it --image=nicolaka/netshoot -- bash
# inside:
nslookup postgres.student-api.svc.cluster.local
nc -zv postgres.student-api.svc.cluster.local 5432
curl -v http://flask-api-service.student-api.svc.cluster.local

# Verify service has endpoints (= backing pods)
kubectl get endpoints postgres -n student-api

# Check kube-proxy iptables rules (advanced)
kubectl exec -n kube-system <kube-proxy-pod> -- iptables-save | grep <service-cluster-ip>

# CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

---

## Interview Q&A

### Architecture & Concepts

| Q | A |
|---|---|
| **What's a Pod?** | The smallest deployable unit. Wraps one or more containers that share network namespace (localhost), storage volumes, and lifecycle. |
| **Pod vs Container?** | Container = a process. Pod = a wrapper around 1+ containers that share resources. K8s schedules pods, not containers. |
| **What's a Deployment?** | A workload controller that manages a ReplicaSet, which manages Pods. Adds rolling updates, rollbacks, and replica count management. |
| **Deployment vs StatefulSet?** | Deployment = stateless, random pod names, shared PVC. StatefulSet = stateful, ordered names (`pg-0`, `pg-1`), per-pod PVC, stable DNS. |
| **What's a DaemonSet?** | Ensures one pod per node. Used for per-node agents (logging, monitoring, CNI). Scales automatically as nodes join/leave. |
| **What's a Job vs CronJob?** | Job = run a pod to completion (one-shot). CronJob = run a Job on a schedule. |
| **What's a namespace?** | Logical isolation of resources within a cluster. Used for multi-tenancy, RBAC scoping, resource quotas, and DNS scoping. |
| **What's a ServiceAccount?** | Identity for processes inside pods. Used for RBAC and authenticating to the K8s API. Distinct from User accounts (which are for humans). |

### Networking

| Q | A |
|---|---|
| **How does pod-to-pod communication work?** | Each pod gets a unique IP from CNI. Routes are set up so pods on different nodes can reach each other directly. No NAT involved. |
| **How does service discovery work?** | CoreDNS in `kube-system` resolves service names to ClusterIPs. Pods get its IP in `/etc/resolv.conf`. Search domains let `postgres` resolve to `postgres.<ns>.svc.cluster.local`. |
| **What does kube-proxy do?** | Watches API server for Services/Endpoints, programs iptables (or IPVS) on every node so traffic to ClusterIP gets DNATed to a pod IP. |
| **ClusterIP vs NodePort vs LoadBalancer?** | ClusterIP = internal only. NodePort = exposed on every node IP at 30000-32767. LoadBalancer = cloud LB provisioned. |
| **What's an Ingress?** | L7 routing rules (HTTP host/path) implemented by an Ingress Controller (nginx, Traefik, ALB). Replaces multiple LoadBalancer services. |
| **What's a Headless Service?** | Service with `clusterIP: None`. DNS returns pod IPs directly (not a single VIP). Used by StatefulSets for per-pod DNS. |
| **What's CNI?** | Container Network Interface — the spec for K8s networking plugins. Implementations: Calico, Cilium, Flannel, Kindnet. Assigns pod IPs and sets up cross-node routing. |
| **What's the difference between iptables and IPVS modes for kube-proxy?** | iptables = linear rules, fine up to ~1000 services. IPVS = kernel hash-table load balancing, scales to tens of thousands of services. |
| **How does external traffic reach a pod?** | External LB → NodePort or Ingress controller → kube-proxy DNATs → pod. Or via ALB Ingress in AWS (ALB directly to pod IPs). |

### Storage

| Q | A |
|---|---|
| **PV vs PVC?** | PV = the actual storage chunk. PVC = a request for storage. PVC binds to a matching PV (or triggers dynamic provisioning). |
| **What's a StorageClass?** | Defines HOW to provision storage — which provisioner, params, reclaim policy. PVCs reference a StorageClass to get matching PVs created on demand. |
| **Access modes?** | RWO = one node RW. RWX = many nodes RW (NFS/EFS). ROX = many nodes RO. RWOP = one pod RW. |
| **Reclaim policies?** | Retain (keep PV after PVC deleted), Delete (remove PV + storage), Recycle (deprecated). |
| **How do you back up a stateful app's data?** | Volume snapshots (CSI snapshots), Velero (cluster-wide backup), application-level dumps (pg_dump) to S3. |
| **How do you migrate a PVC to a new StorageClass?** | Take a snapshot of the original PV; create a new PVC with new StorageClass from the snapshot; update Deployment to use the new PVC. |

### Workloads

| Q | A |
|---|---|
| **What's the default rollout strategy?** | RollingUpdate with `maxSurge=25%`, `maxUnavailable=25%`. Old pods replaced gradually. Zero downtime if probes are correct. |
| **When would you use Recreate strategy?** | When the app can't run two versions simultaneously — e.g., schema migration that breaks the old version. |
| **What are init containers good for?** | One-shot setup: run migrations, fix permissions, wait for dependencies. Run before main containers, in order, must succeed. |
| **What's a sidecar?** | A container that runs alongside the main one for the lifetime of the pod. Use cases: log shipper, service mesh proxy (Envoy), auth proxy. |
| **What's a static pod?** | A pod managed directly by kubelet (not API server). Manifest lives in `/etc/kubernetes/manifests`. Used for control plane components. |

### Probes & Lifecycle

| Q | A |
|---|---|
| **Liveness vs Readiness vs Startup probe?** | Liveness — restart if failing. Readiness — remove from Service if failing. Startup — gate liveness during slow startup. |
| **When would readiness without liveness make sense?** | App that auto-recovers from transient failures but shouldn't receive traffic during them. Restart wouldn't help. |
| **What's a graceful shutdown?** | When K8s sends SIGTERM, the app should stop accepting new requests, finish in-flight ones, then exit. K8s waits `terminationGracePeriodSeconds` (default 30s) before SIGKILL. |
| **What's a PreStop hook?** | A command/HTTP hook K8s runs **before** sending SIGTERM. Useful for de-registering from a load balancer or notifying peers. |

### Autoscaling

| Q | A |
|---|---|
| **HPA vs VPA?** | HPA scales **number of pods** based on CPU/memory/custom metrics. VPA scales **per-pod resources** (CPU/memory requests). Don't use both on the same metric. |
| **What's required for HPA to work?** | metrics-server installed; target Deployment has `resources.requests` defined; HPA references the right metric. |
| **How does HPA decide when to scale?** | Sample interval (default 15s). If `currentMetric/targetMetric * currentReplicas > maxReplicas` → scale up; less → scale down. Uses stabilization windows to avoid flapping. |
| **What's KEDA?** | Event-driven autoscaler. 60+ scalers (Kafka lag, Redis queue, Prometheus query). Can scale to **zero** (HPA can't). Great for event-driven workloads. |
| **What's the Cluster Autoscaler?** | Adds/removes **nodes** when pods can't be scheduled (Pending) or nodes are underutilized. Works with cloud ASGs. |
| **HPA scaling lag — how to reduce?** | Tune `behavior.scaleUp.stabilizationWindowSeconds=0`; use a smaller `--horizontal-pod-autoscaler-sync-period` (default 15s); ensure metrics-server has fresh data. |

### Secrets & Security

| Q | A |
|---|---|
| **K8s Secrets vs Vault?** | K8s Secrets = base64 (NOT encrypted by default), stored in etcd. Vault = encrypted, audited, with rotation, fine-grained policies. ESO bridges them. |
| **How do you encrypt K8s Secrets at rest?** | Configure etcd encryption-at-rest with EncryptionConfiguration (AES-CBC, KMS provider). Or use a sealed-secrets / SOPS / Vault layer. |
| **What's RBAC?** | Role-Based Access Control. `Role`/`ClusterRole` define permissions; `RoleBinding`/`ClusterRoleBinding` grant them to subjects (User, Group, ServiceAccount). |
| **What's PodSecurity?** | Pod Security Standards (PSS): privileged / baseline / restricted. Enforced via Pod Security admission controller. Replaces deprecated PodSecurityPolicy. |
| **Network Policies — when don't they work?** | Only enforced if your CNI supports it (Calico, Cilium, Weave). Flannel/Kindnet do not. |
| **How would you rotate a Vault token used by ESO?** | Generate new token in Vault → `kubectl create secret generic vault-token --from-literal=token=<new>` (overwrites) → ESO picks it up at next sync. |

### Operators & CRDs

| Q | A |
|---|---|
| **What's a CRD?** | Custom Resource Definition — extends K8s API with new resource types. Once installed, you can `kubectl apply` instances of that type. |
| **CRD vs CR vs Operator?** | CRD = schema (`ExternalSecret`). CR = instance of that CRD. Operator = controller that watches and reconciles CRs. |
| **Why use an operator over a Helm chart?** | Helm = one-shot templating. Operator = continuous reconciliation, automated ops (backup, failover, scaling). Operators encode domain logic. |
| **Give an example of an operator from this project.** | ESO — watches `ExternalSecret` resources and continuously syncs from Vault to K8s Secrets. Vault Operator (production) — manages Vault clusters with auto-init and unseal. |
| **What's an admission webhook?** | HTTPS endpoint K8s calls during resource create/update to validate (`ValidatingWebhook`) or modify (`MutatingWebhook`). ESO uses one to validate ExternalSecret resources. |

### Real Production Scenarios

| Q | A |
|---|---|
| **A pod is in CrashLoopBackOff. Walk me through your debugging.** | (1) `kubectl describe pod` for events. (2) `kubectl logs --previous` for crash output. (3) Check init container logs separately. (4) Verify env vars: `kubectl exec ... -- env`. (5) Verify mounted secrets exist. (6) Run debug pod with same image. |
| **A Service is unreachable. What do you check?** | DNS (`nslookup` from a debug pod), Service has Endpoints (`kubectl get ep`), correct selector (`kubectl describe svc`), Pod readiness probe passing, NetworkPolicy not blocking, port matches container port, app binding to 0.0.0.0. |
| **How do you do zero-downtime deployments?** | RollingUpdate strategy + readiness probes that ONLY return ready when app can handle requests + `maxUnavailable=0` + PreStop hook for graceful shutdown + `terminationGracePeriodSeconds` long enough to drain. |
| **Pods are pending — what's wrong?** | `kubectl describe pod` Events: insufficient CPU/memory, PVC unbound, no node matching nodeSelector/affinity, taints not tolerated. |
| **How do you handle migrations in K8s?** | Init container runs `flask db upgrade` before the main container. Guarantees schema is up-to-date before app accepts traffic. For complex migrations: a separate Job before deploying. |
| **What if migration fails?** | Init container exits non-zero → main container never starts → pod status shows init failure. Fix migration, redeploy. |
| **How do you upgrade a stateful app like Postgres?** | StatefulSet with rolling update. Take backup first. Test in staging. Use partition strategy for canary (e.g., update only postgres-2 first). |
| **How do you scale based on custom metrics?** | KEDA with a Prometheus scaler, OR HPA with `prometheus-adapter` (registers Prometheus metrics as K8s metrics). |
| **A namespace is stuck Terminating. What do you do?** | Find the resource with stuck finalizers: `kubectl api-resources --verbs=list --namespaced -o name \| xargs -n 1 kubectl get -n <ns>`. Patch finalizers to null: `kubectl patch <resource> -p '{"metadata":{"finalizers":null}}' --type=merge`. |

---

## STAR Stories

### Story 1: "Tell me about a time you debugged pod-to-pod connectivity."

**Situation:** After deploying our Flask app to K8s, port-forwarding to the Service returned `Connection reset by peer`. Pods showed `1/1 Running`, no errors in logs.

**Task:** Diagnose why a Running pod was unreachable.

**Action:**
1. Verified Service had Endpoints: `kubectl get endpoints flask-api-service` — endpoints were listed, so Service knew about the pods.
2. Verified port-forward was hitting the right Service: `kubectl describe svc flask-api-service` — port 80 → targetPort 5000, correct.
3. Curled the pod IP directly from a debug pod (`nicolaka/netshoot`): also failed.
4. Checked Gunicorn logs more carefully — saw `Listening at http://127.0.0.1:8000`. **Loopback only.**
5. Set `GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000` env var in the Deployment.
6. Rolled the deployment; port-forward worked immediately.

**Result:** API reachable. Same lesson applies in cloud — apps must bind to `0.0.0.0` for K8s Service routing to work.

**Takeaway:** "Pod Running" does NOT mean "pod reachable." Always verify the app is bound to the right interface (0.0.0.0, not 127.0.0.1).

---

### Story 2: "Tell me about a time you debugged a stuck namespace."

**Situation:** During cleanup, I deleted `k8s/external-secrets-store.yaml` to recreate the ExternalSecret. The `student-api` namespace went into `Terminating` and never finished — blocking other deploys.

**Task:** Force the namespace to finish terminating without losing other resources.

**Action:**
1. `kubectl get ns student-api -o json` showed condition `SomeFinalizersRemain: externalsecrets.external-secrets.io/externalsecret-cleanup`.
2. ExternalSecret had a finalizer, but the ESO controller had already been uninstalled — so the finalizer would never be removed by the controller.
3. Patched the finalizer to null: `kubectl patch externalsecret studentdb-secrets -n student-api -p '{"metadata":{"finalizers":null}}' --type=merge`.
4. Namespace immediately finished terminating.

**Result:** Unblocked the cleanup. Documented in our runbook: "If you uninstall an operator, delete its CRs first; otherwise their finalizers strand resources."

**Takeaway:** Finalizers are powerful but can deadlock when the controller that owns them is gone. Always order: delete CRs → uninstall controller → uninstall CRDs.

---

### Story 3: "Tell me about a time you fixed an unbootable pod due to PVC permissions."

**Situation:** Deployed Vault to minikube. Pod CrashLoopBackOff with `mkdir /vault/data: permission denied` even though we set `securityContext: { runAsUser: 100, fsGroup: 1000 }`.

**Task:** Fix Vault startup without disabling security context.

**Action:**
1. Inspected pod spec — confirmed `fsGroup: 1000` was set on PodSecurityContext.
2. Realized minikube's hostpath provisioner doesn't honor `fsGroup` chown for newly-created PVs.
3. SSHed into the node where Vault was scheduled: `minikube ssh -n minikube-m03`.
4. Located the PV directory: `/var/hostpath-provisioner/vault/vault-pvc/`.
5. `sudo chown -R 100:1000 /var/hostpath-provisioner/vault/vault-pvc/`.
6. Deleted the Vault pod; restarted with same securityContext — Vault initialized cleanly.

**Result:** Vault came up. Long-term fix: add an `initContainer` that runs `chown -R 100:1000 /vault/data` as root before Vault starts (works on any K8s, not just minikube).

**Takeaway:** `fsGroup` works in cloud (EBS, GCE PD) but not always on local provisioners. Init containers as root are the portable fix for permission setup.

---

### Story 4: "Tell me about a time you implemented HPA in production."

**Situation:** Our Flask API was over-provisioned at 10 replicas during off-peak hours. CFO wanted cost reduction without sacrificing peak performance.

**Task:** Implement autoscaling that handles 10x traffic spikes but scales down to save money at night.

**Action:**
1. Confirmed `metrics-server` was running and pods had `resources.requests` set (HPA needs both).
2. Wrote HPA: `minReplicas: 2`, `maxReplicas: 20`, target CPU 70%, target memory 80%.
3. Tuned scale-down behavior: `stabilizationWindowSeconds: 600` (10 min) — avoid flapping during traffic dips.
4. Tuned scale-up: `policies: [{type: Percent, value: 100, periodSeconds: 60}]` — double pods every minute when needed.
5. Load-tested with Locust at 10x normal traffic — HPA scaled to 18 in ~2 minutes.
6. Watched scale-down at night (off-peak); reached 2 replicas after 10 min stabilization window.

**Result:** Compute cost dropped 40% on average. Peak-hour latency unchanged. Set up a Grafana dashboard tracking `hpa_current_replicas` so we could spot anomalies.

**Takeaway:** HPA + good probes + cluster autoscaler = elastic infrastructure. Stabilization windows are critical to avoid flap loops; tune scale-up aggressive, scale-down patient.

---

## Production Hardening

### Cluster

| Area | Current | Production |
|------|---------|-----------|
| **Cluster** | minikube (single host) | EKS / GKE / AKS — managed control plane, multi-AZ |
| **Nodes** | 3 minikube nodes | Node groups per workload class (app/db/infra), spot for stateless |
| **Networking** | Kindnet | Calico / Cilium — supports NetworkPolicy, eBPF observability |
| **DNS** | CoreDNS default | CoreDNS HPA, NodeLocal DNSCache for performance |
| **Storage** | hostpath | EBS gp3 (cloud) with CSI driver, snapshots configured |
| **Auth** | minikube admin | OIDC SSO (Google/Okta), short-lived tokens |
| **RBAC** | Default | Least-privilege: per-team Roles, no cluster-admin for humans |

### Workload

| Area | Current | Production |
|------|---------|-----------|
| **Probes** | Some pods | Liveness + readiness on every workload; startup for slow apps |
| **Resources** | Some have limits | Every pod has requests + limits; quotas per namespace |
| **HPA** | Not deployed | HPA on app workloads; Cluster Autoscaler on nodes |
| **PDB (PodDisruptionBudget)** | None | `minAvailable` for stateful apps to survive node drain |
| **Affinity** | Simple nodeSelector | Pod anti-affinity to spread replicas across AZs |
| **Image pull policy** | Default | `Always` for `:latest`; `IfNotPresent` for SHA-pinned |
| **Image source** | DockerHub | Private registry (ECR/GCR/ACR); image scanning in CI |

### Security

| Area | Current | Production |
|------|---------|-----------|
| **Secrets** | Vault + ESO | Same, plus auto-unseal with cloud KMS |
| **NetworkPolicies** | None | Default-deny + explicit allow rules |
| **PodSecurity** | Default | Enforce `restricted` Pod Security Standard via PSA admission |
| **Image signing** | None | Cosign + admission controller (Sigstore) |
| **Audit logging** | Default | Audit policy → SIEM (CloudWatch, Splunk) |
| **Service mesh** | None | Istio / Linkerd for mTLS, traffic policies, observability |

### Observability (covered in Module 7)

| Area | Production |
|------|-----------|
| Metrics | Prometheus + Grafana |
| Logs | Loki + Promtail |
| Traces | Jaeger / Tempo + OpenTelemetry SDK in apps |
| Alerts | Alertmanager → Slack / PagerDuty |

---

## Cloud Mapping

### Minikube → Cloud Managed K8s

| minikube | AWS EKS | GCP GKE | Azure AKS |
|----------|---------|---------|-----------|
| `minikube start --nodes=3` | EKS cluster + 3 worker nodes (managed node group) | GKE Autopilot or Standard | AKS cluster |
| Single host | Multi-AZ control plane | Regional cluster | Availability Zone-based |
| hostpath PV | EBS via CSI | Persistent Disk | Azure Disk |
| LoadBalancer | Network LB / ALB | Cloud LB | Standard LB |
| Ingress (manual install) | AWS Load Balancer Controller (ALB) | GKE Ingress (Cloud LB) | App Gateway Ingress Controller |
| ServiceAccount | IRSA (IAM Roles for Service Accounts) | Workload Identity | Pod-managed identity |
| ConfigMap | Same | Same | Same |
| Secret | Same; AWS Secrets Manager via Secrets Store CSI | Secret Manager via CSI | Key Vault via CSI |
| Static node | Auto Scaling Group | Managed Instance Group | VM Scale Set |

### Why managed K8s?

- Control plane managed (etcd, API server, scheduler) — you only manage workloads
- Multi-AZ HA out of the box
- Integrated with cloud IAM (no need to manage K8s users separately)
- Auto-upgrades, security patches handled
- Cost: $73/month per cluster (EKS) on top of node costs

---

## Reference Links (Internal)

- Cluster setup notes: this doc
- Vault manifest: [k8s/vault.yaml](../k8s/vault.yaml)
- ESO store + secrets: [k8s/external-secrets-store.yaml](../k8s/external-secrets-store.yaml)
- Database: [k8s/database.yaml](../k8s/database.yaml)
- Application: [k8s/application.yaml](../k8s/application.yaml)
- Helm charts (Module 6): [helm/](../helm/)
- ArgoCD apps (Module 6): [argocd/](../argocd/)
