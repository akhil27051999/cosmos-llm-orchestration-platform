# Observability Stack — Complete Documentation

End-to-end observability setup for the Flask Student API project using **Prometheus, Loki, Grafana, Promtail, Alertmanager**, and exporters — all GitOps-managed via ArgoCD.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Components](#components)
3. [File Structure](#file-structure)
4. [Setup Commands](#setup-commands)
5. [Application Code Changes](#application-code-changes)
6. [Alert Rules](#alert-rules)
7. [Grafana Dashboards](#grafana-dashboards)
8. [Slack Integration](#slack-integration)
9. [Verification & Screenshots](#verification--screenshots)
10. [Troubleshooting](#troubleshooting)
11. [Useful Queries](#useful-queries)
12. [Production Hardening](#production-hardening)
13. [Interview Talking Points](#interview-talking-points)

---

## Architecture

```
                         observability namespace
                         (minikube-m03 / type=dependent_services)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌─────────┐         ┌──────────┐          ┌──────────┐
   │Prometheus│────────│Alertmanager│──────►│  Slack   │
   │  + AM    │         │           │        │ #alerts  │
   └────▲─────┘         └──────────┘        └──────────┘
        │ scrapes
        │
   ┌────┴───────────────────────────────────────┐
   │                                             │
┌──┴──────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│Flask App│  │postgres │  │blackbox │  │node/kube│
│ /metrics│  │exporter │  │exporter │  │ -state  │
└─────────┘  └─────────┘  └─────────┘  └─────────┘
   ▲
   │ logs (file paths)
┌──┴──────┐         ┌──────────┐           ┌────────┐
│Promtail │────────►│   Loki   │◄──────────│Grafana │
│DaemonSet│  push   │ (storage)│   query   │  (UI)  │
└─────────┘         └──────────┘           └────────┘
```

---

## Components

| Component | Chart | Purpose |
|-----------|-------|---------|
| **Prometheus** | `prometheus-community/prometheus` | Metrics scraping + alert rules |
| **Alertmanager** | bundled in Prometheus | Alert routing → Slack |
| **node-exporter** | bundled in Prometheus | Node-level metrics (CPU/mem/disk/net) |
| **kube-state-metrics** | bundled in Prometheus | K8s object state (pods, deployments, etc.) |
| **Grafana** | `grafana/grafana` | Dashboards & visualization |
| **Loki** | `grafana/loki` (single binary) | Log storage & query |
| **Promtail** | `grafana/promtail` | Log shipper (DaemonSet) |
| **Postgres Exporter** | `prometheus-community/prometheus-postgres-exporter` | DB metrics |
| **Blackbox Exporter** | `prometheus-community/prometheus-blackbox-exporter` | Endpoint uptime/latency probes |

---

## File Structure

```
helm/
├── prometheus/values.yaml         # Prometheus + Alertmanager + alert rules + scrape configs
├── grafana/values.yaml            # Grafana + datasources + 5 pre-loaded dashboards
├── loki/values.yaml               # Loki single binary + permission fix
├── promtail/values.yaml           # Promtail filtering only student-api logs
├── postgres-exporter/values.yaml  # DB exporter — reads postgres-secret
└── blackbox-exporter/values.yaml  # HTTP probe exporter

argocd/
├── observability-prometheus.yaml         # ArgoCD app: Prometheus
├── observability-grafana.yaml            # ArgoCD app: Grafana
├── observability-loki.yaml               # ArgoCD app: Loki
├── observability-promtail.yaml           # ArgoCD app: Promtail
├── observability-postgres-exporter.yaml  # ArgoCD app: Postgres exporter
└── observability-blackbox-exporter.yaml  # ArgoCD app: Blackbox exporter
```

---

## Setup Commands

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Apply observability ArgoCD apps | `kubectl apply -f argocd/observability-*.yaml` | ArgoCD provisions all 6 components |
| 2 | Wait for pods to come up | `kubectl get pods -n observability -w` | Watch until everything is `Running` |
| 3 | Fix PV permissions on hostpath (one-time) | `minikube ssh -n minikube-m03 "sudo chown -R 65534:65534 /var/hostpath-provisioner/observability/prometheus-server"` | minikube hostpath provisioner doesn't honor `fsGroup` for new PVCs |
| 4 | Fix Loki PV permissions | `minikube ssh -n minikube-m03 "sudo chown -R 10001:10001 /var/hostpath-provisioner/observability/storage-loki-0"` | Same reason as above |
| 5 | Create Slack webhook secret (out-of-band) | `kubectl create secret generic alertmanager-slack-webhook --from-literal=slack_url=<webhook-url> -n observability` | Secret can't live in Git (GitHub Push Protection blocks it) |
| 6 | Sync postgres-secret to observability ns | Auto-synced via ESO `postgres-secret-observability` ExternalSecret | postgres-exporter needs DB credentials in its own namespace |
| 7 | Port-forward Grafana | `kubectl port-forward -n observability svc/grafana 3000:80` | Access UI at http://localhost:3000 |
| 8 | Get Grafana password | `kubectl get secret grafana -n observability -o jsonpath='{.data.admin-password}' \| base64 -d` | Default admin login |
| 9 | Verify Prometheus targets | `kubectl exec -n observability deploy/prometheus-server -c prometheus-server -- wget -qO- http://localhost:9090/api/v1/targets` | List all scrape targets and their health |
| 10 | Test alert manually | `curl -XPOST localhost:9093/api/v2/alerts -d '[{...}]'` | Verify Alertmanager → Slack pipeline |

---

## Application Code Changes

To get Flask metrics into Prometheus, you must instrument the app:

### `app/requirements.txt`
```
prometheus-flask-exporter==0.23.1
```

### `app/__init__.py`
```python
from prometheus_flask_exporter import PrometheusMetrics

def create_app():
    app = Flask(__name__)
    # ... existing setup ...
    PrometheusMetrics(app)   # exposes /metrics endpoint
    return app
```

**Result:** Flask now exposes `/metrics` with default request metrics:
- `flask_http_request_total{method,status,path}`
- `flask_http_request_duration_seconds_bucket{...}`
- `flask_http_request_duration_seconds_count{...}`

> **⚠️ Test gotcha:** Don't call `metrics.info('flask_app_info', ...)` — it registers in the global Prometheus registry and fails with `Duplicated timeseries` when tests create the app multiple times.

---

## Alert Rules

Defined in [helm/prometheus/values.yaml](../helm/prometheus/values.yaml) under `serverFiles.alerting_rules.yml`:

| Alert | Threshold | Severity | Use Case |
|-------|-----------|----------|----------|
| **HighCPUUsage** | CPU > 80% for 5m | warning | Node overload |
| **HighDiskUsage** | Disk > 85% for 5m | warning | Disk filling up |
| **HighRequestRate** | Flask req/s > 100 for 5m | warning | Traffic spike |
| **ErrorRateSpike** | 5xx > 5% in 10m | critical | Service degradation |
| **HighP99Latency** | p99 > 1s for 5m | warning | Slow responses |
| **VaultPodRestarted** | Vault restart in 5m | critical | Secrets infra failure |
| **ArgoCDServerRestarted** | ArgoCD restart in 5m | critical | GitOps controller down |
| **PostgresPodRestarted** | Postgres restart in 5m | critical | DB instability |
| **EndpointDown** | Blackbox probe fails for 2m | critical | Service unreachable |
| **HighEndpointLatency** | Probe duration > 1s for 5m | warning | Slow endpoints |

---

## Grafana Dashboards

Pre-loaded via [helm/grafana/values.yaml](../helm/grafana/values.yaml) using `gnetId` (from grafana.com/dashboards):

| ID | Name | Datasource | Description |
|----|------|-----------|-------------|
| 1860 | Node Exporter Full | Prometheus | Comprehensive node metrics |
| 7249 | Kubernetes Cluster | Prometheus | Cluster overview (pods, restarts, CPU, memory) |
| 9628 | PostgreSQL Database | Prometheus | DB metrics from postgres-exporter |
| 7587 | Prometheus Blackbox Exporter | Prometheus | Endpoint uptime/latency |
| 13639 | Logs / App | Loki | Application log search |

---

## Slack Integration

| Step | Description |
|------|-------------|
| 1 | Create Slack app at `api.slack.com/apps` → "Create New App" → "From scratch" |
| 2 | **Features → Incoming Webhooks** → Activate → **Add New Webhook to Workspace** → pick channel |
| 3 | Copy webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`) |
| 4 | Create K8s secret (don't commit URL to git!): `kubectl create secret generic alertmanager-slack-webhook --from-literal=slack_url=<URL> -n observability` |
| 5 | Alertmanager values reference: `slack_api_url_file: /etc/alertmanager/secrets/slack_url` |
| 6 | Mount via `extraSecretMounts` in chart values |

---

## Verification & Screenshots

### 1. Prometheus Targets — All Up

Run in Grafana → Explore → Prometheus:
```promql
up
```

Expected: 1 for every job (`flask-api`, `postgres-exporter`, `blackbox-http`, `kubernetes-nodes`, etc.)

![Prometheus up query](images/observability/grafana-up-query.png)

### 2. Flask App Metrics

```promql
flask_http_request_total
```

Should return one series per pod (e.g., 3 replicas) with `method`, `status` labels.

![Flask HTTP metrics](images/observability/grafana-flask-metrics.png)

### 3. Kubernetes Cluster Dashboard

Pre-loaded dashboard showing node CPU/memory, pod counts, restarts.

![Kubernetes Cluster Dashboard](images/observability/grafana-k8s-cluster-dashboard.png)

### 4. Node Exporter Dashboard

Comprehensive per-node metrics: CPU, memory, network, disk.

![Node Exporter Full Dashboard](images/observability/grafana-node-exporter-dashboard.png)

### 5. PostgreSQL Dashboard

Shows DB connections, query rate, transaction commits, table sizes.

![PostgreSQL Dashboard](images/observability/grafana-postgres-dashboard.png)

### 6. Blackbox Exporter Dashboard

Endpoint uptime, HTTP status codes, probe duration for Flask, ArgoCD, Vault.

![Blackbox Exporter Dashboard](images/observability/grafana-blackbox-dashboard.png)

### 7. Loki Logs (via Explore)

Query: `{namespace="student-api"}`

Streams Flask app logs in real-time.

![Loki Logs Explore](images/observability/grafana-loki-explore.png)

### 8. Loki Logs with Field Filtering

Same query, table view with extracted fields (container, app, namespace, pod).

![Loki Logs with Fields](images/observability/grafana-loki-fields.png)

### 9. Slack Alerts

Real alerts firing in `#alerts` channel — `EndpointDown`, `TestAlert`, with severity, summary, description.

![Slack Alerts](images/observability/slack-alerts.png)

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | Prometheus pod CrashLoopBackOff: `permission denied: /data/queries.active` | minikube hostpath provisioner doesn't apply `fsGroup` chown to existing PV directory | SSH to node and `chown -R 65534:65534 /var/hostpath-provisioner/observability/prometheus-server` |
| 2 | Loki pod CrashLoopBackOff: `mkdir /var/loki/rules: permission denied` | Same as above | `chown -R 10001:10001 /var/hostpath-provisioner/observability/storage-loki-0` |
| 3 | Alertmanager: `unsupported scheme "" for URL` | `${SLACK_WEBHOOK_URL}` placeholder in config wasn't substituted | Use real URL OR move to `slack_api_url_file` reading from K8s secret |
| 4 | Alertmanager: `field not declared in schema (fsGroup)` | Schema validation: `fsGroup` is pod-level, not container-level | Use `podSecurityContext` instead of `securityContext` for fsGroup |
| 5 | postgres-exporter: `secret "postgres-secret" not found` | Secret only exists in `student-api` namespace | Add ESO ExternalSecret to also create it in `observability` ns |
| 6 | postgres-exporter: `expected string; got float64` | Chart's helper template expects `port` as string | `port: "5432"` (quoted) instead of `port: 5432` |
| 7 | Prometheus: custom scrape configs not appearing in config | `extraScrapeConfigs` was nested under `server:` but is a top-level field | Move `extraScrapeConfigs` to root level of values.yaml |
| 8 | Prometheus: `flask-api 404 NOT FOUND` on /metrics | App didn't expose Prometheus metrics | Add `prometheus-flask-exporter` to requirements.txt + `PrometheusMetrics(app)` to __init__.py |
| 9 | Tests fail: `Duplicated timeseries in CollectorRegistry: flask_app_info` | `metrics.info()` registers in global registry; conflicts when tests create app multiple times | Drop `metrics.info()` line — base `PrometheusMetrics(app)` is sufficient |
| 10 | Grafana: `Post .../api/v1/query_range: i/o timeout` | Datasource URL missing port (defaulted to 80, Prometheus is on 9090) | URL must include `:9090` |
| 11 | EndpointDown alert firing for ArgoCD | ArgoCD redirects HTTP→HTTPS (returns 307); blackbox only accepted 200/201 | Update blackbox `valid_status_codes: [200, 201, 301, 302, 307, 308]` |
| 12 | GitHub Push Protection: "Push cannot contain secrets" | Slack webhook URL committed to values.yaml | Move webhook to K8s Secret + use Alertmanager's `slack_api_url_file`; rewrite history with `git reset --soft HEAD~N && git commit` |
| 13 | Promtail pods 0/1 ready on some nodes | Readiness probe fails because no `student-api` pods on those nodes (no logs to ship) | Expected — harmless. Promtail still functional. |
| 14 | Loki dashboard "no data" but Explore works | Dashboard 13639 expects different label names than what Promtail ships | Use Explore for ad-hoc queries; replace dashboard if needed |

---

## Useful Queries

### PromQL (Metrics)

| Query | What It Shows |
|-------|--------------|
| `up` | All scrape targets and their health (1 = up, 0 = down) |
| `flask_http_request_total` | Total Flask requests by route/method/status |
| `rate(flask_http_request_total[1m])` | Flask requests per second |
| `histogram_quantile(0.99, rate(flask_http_request_duration_seconds_bucket[5m]))` | p99 latency |
| `pg_database_size_bytes` | Postgres DB sizes |
| `pg_stat_database_xact_commit` | DB commit count |
| `probe_success` | Blackbox endpoint health (1/0) |
| `probe_duration_seconds` | Endpoint response time |
| `100 - (avg by(instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` | CPU usage % per node |
| `node_filesystem_avail_bytes / node_filesystem_size_bytes * 100` | Disk free % |
| `kube_pod_container_status_restarts_total` | Pod restart counts |

### LogQL (Loki)

| Query | What It Shows |
|-------|--------------|
| `{namespace="student-api"}` | All Flask app logs |
| `{app="flask-api"} \|= "ERROR"` | Only error log lines |
| `{app="flask-api"} \|~ "students/[0-9]+"` | Logs matching student endpoint regex |
| `count_over_time({app="flask-api"} \|= "ERROR" [5m])` | Error count over 5 min |
| `rate({app="flask-api"} \|= "ERROR" [1m])` | Error rate per second |

---

## Quick Health Check

```bash
# All apps healthy?
kubectl get applications -n argocd

# All pods running?
kubectl get pods -n observability

# Prometheus targets up?
kubectl exec -n observability deploy/prometheus-server -c prometheus-server \
  -- wget -qO- http://localhost:9090/api/v1/targets \
  | python3 -c "import sys,json; [print(t['labels']['job'], t['health']) for t in json.load(sys.stdin)['data']['activeTargets']]"

# Active alerts?
kubectl exec -n observability prometheus-alertmanager-0 \
  -- wget -qO- http://localhost:9093/api/v2/alerts

# Logs flowing into Loki?
kubectl exec -n observability deploy/grafana \
  -- wget -qO- "http://loki.observability.svc.cluster.local:3100/loki/api/v1/labels"
```

---

## Production Hardening

| Area | Current | Production |
|------|---------|-----------|
| **Storage** | hostpath (lost on minikube delete) | EBS / persistent storage with backups |
| **HA** | Single Prometheus, single Loki | Prometheus HA pair + Thanos for long-term; Loki distributed mode |
| **Retention** | 7 days | 30+ days for metrics, 90+ for logs |
| **Loki backend** | filesystem | S3 / GCS for object storage |
| **Alerting** | Slack only | Slack + PagerDuty + email + dedup via Opsgenie |
| **TLS** | None | Cert-manager + auto-renewed certs for all UIs |
| **Auth** | Grafana admin/admin | OIDC SSO (Google/Okta) for Grafana, Prometheus, Alertmanager |
| **Tracing** | Not implemented | Jaeger or Tempo + OpenTelemetry SDKs in apps |
| **Dashboards** | gnetId community dashboards | Custom dashboards in JSON committed to Git, version-controlled |
| **Recording rules** | None | Pre-aggregate expensive queries (`record:` rules in Prometheus) |
| **Alert routing** | All to one Slack channel | Routes by team/severity/service via Alertmanager `routes` |
| **Webhook secrets** | K8s Secret (one-off kubectl create) | Vault + ESO sync (already have ESO!) |

---

## Interview Talking Points

### Observability Pillars

| Pillar | What It Answers | Tools in Our Stack |
|--------|----------------|--------------------|
| **Metrics** | "How is the system performing?" (req/s, latency, CPU) | Prometheus + Grafana |
| **Logs** | "What happened?" (errors, events, traces of user actions) | Loki + Promtail + Grafana |
| **Traces** | "Why is it slow?" (request flow across services) | Not implemented — would use Jaeger/Tempo |

### USE Method (for Resources)

| Letter | Meaning | Example Query |
|--------|---------|---------------|
| **U**tilization | % time resource is busy | `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| **S**aturation | Queue/wait length | `node_load1 / count(node_cpu_seconds_total{mode="idle"}) by (instance)` |
| **E**rrors | Error count | `rate(node_disk_io_errors_total[5m])` |

### RED Method (for Services)

| Letter | Meaning | Example Query |
|--------|---------|---------------|
| **R**ate | Requests per second | `rate(flask_http_request_total[1m])` |
| **E**rrors | Error rate | `rate(flask_http_request_total{status=~"5.."}[5m])` |
| **D**uration | Latency p95/p99 | `histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))` |

### Common Q&A

| Q | A |
|---|---|
| **Prometheus vs Loki?** | Prometheus = time-series numerical metrics (CPU, req/s). Loki = log aggregation (text events). Both queried in Grafana via PromQL/LogQL. |
| **Why Loki over ELK?** | Loki indexes only metadata (labels), not log content — much cheaper at scale. ELK is more flexible but heavier. |
| **Why Promtail not Fluentd/Fluent Bit?** | Promtail is purpose-built for Loki, simpler config. Fluentd/Fluent Bit are more general-purpose log forwarders. |
| **Pull vs Push for metrics?** | Prometheus pulls from `/metrics` endpoints (better for service discovery). Push gateway exists for short-lived jobs. |
| **What's a ServiceMonitor?** | A CRD from Prometheus Operator that auto-generates scrape configs for K8s Services. We used static `extraScrapeConfigs` instead. |
| **How does Alertmanager dedupe alerts?** | Groups by labels (`group_by`), waits `group_wait` for similar alerts, then sends together. Re-fires every `repeat_interval` if still firing. |
| **USE vs RED?** | USE = resource health (Utilization, Saturation, Errors) — for nodes/disks. RED = service health (Rate, Errors, Duration) — for APIs. |
| **Cardinality issues in Prometheus?** | High-cardinality labels (e.g., user_id) create millions of time-series — explodes memory. Stick to bounded label values. |
| **How do you scale Prometheus?** | Federation (HA pairs scrape same targets, query both), Thanos / Mimir for long-term storage and global query. |

---

## Multi-Source ArgoCD Pattern

Each observability ArgoCD Application combines:
- **Source 1:** External Helm chart (e.g., `prometheus-community/prometheus`)
- **Source 2:** Local Git repo with custom `values.yaml`

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
      ref: values    # ← named reference used above
```

This avoids vendoring upstream charts in your repo while keeping all customization in Git.

---

## Permission Errors on Minikube Hostpath (Common Pattern)

For any chart that uses persistent volumes on minikube:

| Step | Action |
|------|--------|
| 1 | List PVC storage paths on the node | `minikube ssh -n minikube-m03 "sudo ls /var/hostpath-provisioner/observability/"` |
| 2 | Get the UID/GID expected by the chart's runAsUser | Check chart values or pod spec |
| 3 | chown the directory | `minikube ssh -n minikube-m03 "sudo chown -R <uid>:<gid> /var/hostpath-provisioner/observability/<pvc-name>"` |
| 4 | Restart the pod | `kubectl delete pod -n observability <pod> --force --grace-period=0` |

This is a **minikube-specific workaround**. In production K8s with EBS/GCE PD, `fsGroup` works correctly out of the box.
