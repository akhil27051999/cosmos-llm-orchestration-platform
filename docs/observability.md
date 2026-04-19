# Module 7: Observability — Prometheus, Loki, Grafana, Alertmanager

> **Goal:** Build a full-stack observability layer — metrics (Prometheus), logs (Loki), dashboards (Grafana), and alerts (Alertmanager → Slack) — all GitOps-managed via ArgoCD.

> **Why this matters:** "You can't fix what you can't see." Observability is the difference between an SRE who diagnoses a production incident in 5 minutes and one who guesses for hours. Every 3-5 yr DevOps/SRE role requires deep familiarity with Prometheus + Grafana, alerting workflows, USE/RED methods, and log aggregation patterns.

---

## Table of Contents

1. [Three Pillars of Observability](#three-pillars-of-observability)
2. [Architecture](#architecture)
3. [Components](#components)
4. [USE & RED Methods](#use--red-methods)
5. [Setup Walkthrough](#setup-walkthrough)
6. [Application Code Changes](#application-code-changes)
7. [Alert Rules](#alert-rules)
8. [Grafana Dashboards](#grafana-dashboards)
9. [Slack Integration](#slack-integration)
10. [Verification](#verification)
11. [Commands Reference](#commands-reference)
12. [Useful Queries](#useful-queries)
13. [Troubleshooting](#troubleshooting)
14. [Interview Q&A](#interview-qa)
15. [STAR Stories](#star-stories)
16. [Production Hardening](#production-hardening)
17. [Cloud Mapping](#cloud-mapping)

---

## Three Pillars of Observability

| Pillar | Question Answered | Tools in Our Stack |
|--------|------------------|--------------------|
| **Metrics** | "How is the system performing?" (req/s, latency, CPU%) | Prometheus + Grafana |
| **Logs** | "What happened?" (errors, events, user actions) | Loki + Promtail + Grafana |
| **Traces** | "Why is it slow? Where did time go?" (request flow across services) | Not implemented — would use Jaeger/Tempo + OpenTelemetry |

A mature stack uses all three. We covered the first two. **Traces** are typically added next as systems grow microservices-heavy.

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

| Component | Helm Chart | Purpose |
|-----------|------------|---------|
| **Prometheus** | `prometheus-community/prometheus` | Metrics scraping + alert rule evaluation |
| **Alertmanager** | bundled in Prometheus | Alert routing (groups, dedup, sends to Slack/email/PagerDuty) |
| **node-exporter** | bundled in Prometheus | DaemonSet — per-node metrics (CPU/mem/disk/net) |
| **kube-state-metrics** | bundled in Prometheus | K8s object state (pod restarts, deployments, etc.) |
| **Grafana** | `grafana/grafana` | Dashboards & visualization |
| **Loki** | `grafana/loki` (single binary mode) | Log storage + query (LogQL) |
| **Promtail** | `grafana/promtail` | Log shipper (DaemonSet) — tails log files, ships to Loki |
| **Postgres Exporter** | `prometheus-community/prometheus-postgres-exporter` | DB-specific metrics (connections, queries, replication lag) |
| **Blackbox Exporter** | `prometheus-community/prometheus-blackbox-exporter` | HTTP/TCP/ICMP probes — endpoint uptime/latency |

---

## USE & RED Methods

Two industry-standard frameworks for choosing what metrics to track.

### USE Method — for Resources (Brendan Gregg)

| Letter | Meaning | Example Query |
|--------|---------|---------------|
| **U**tilization | % time resource is busy | `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| **S**aturation | Queue/wait length | `node_load1 / count(node_cpu_seconds_total{mode="idle"}) by (instance)` |
| **E**rrors | Error count | `rate(node_disk_io_errors_total[5m])` |

Use for **infrastructure**: nodes, disks, network interfaces.

### RED Method — for Services (Tom Wilkie / Weaveworks)

| Letter | Meaning | Example Query |
|--------|---------|---------------|
| **R**ate | Requests per second | `rate(flask_http_request_total[1m])` |
| **E**rrors | Error rate | `rate(flask_http_request_total{status=~"5.."}[5m])` |
| **D**uration | Latency p95/p99 | `histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))` |

Use for **services / APIs**: anything that handles requests.

### The Four Golden Signals (Google SRE Book)

Latency, Traffic, Errors, Saturation. Combination of USE + RED. Same idea, different acronym.

---

## Setup Walkthrough

### File Structure

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

All charts use the **multi-source ArgoCD pattern** — pull upstream chart from Helm repo, override with local `values.yaml`.

### Step-by-Step Commands

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Apply ArgoCD apps | `kubectl apply -f argocd/observability-*.yaml` | ArgoCD provisions all 6 components |
| 2 | Wait for pods | `kubectl get pods -n observability -w` | Watch until everything is `Running` |
| 3 | Fix Prometheus PV permissions (one-time minikube workaround) | `minikube ssh -n minikube-m03 "sudo chown -R 65534:65534 /var/hostpath-provisioner/observability/prometheus-server"` | hostpath provisioner doesn't honor `fsGroup` for new PVCs |
| 4 | Fix Loki PV permissions | `minikube ssh -n minikube-m03 "sudo chown -R 10001:10001 /var/hostpath-provisioner/observability/storage-loki-0"` | Same |
| 5 | Create Slack webhook secret | `kubectl create secret generic alertmanager-slack-webhook --from-literal=slack_url=<webhook> -n observability` | Out-of-band — secret can't live in Git (Push Protection) |
| 6 | Sync postgres-secret to observability ns (via ESO) | Add `postgres-secret-observability` ExternalSecret in `helm/external-secrets/values.yaml` | postgres-exporter needs DB creds in its own namespace |
| 7 | Port-forward Grafana | `kubectl port-forward -n observability svc/grafana 3000:80` | Open http://localhost:3000 |
| 8 | Get Grafana password | `kubectl get secret grafana -n observability -o jsonpath='{.data.admin-password}' \| base64 -d` | Initial admin login |
| 9 | Verify Prometheus targets | `kubectl exec -n observability deploy/prometheus-server -c prometheus-server -- wget -qO- http://localhost:9090/api/v1/targets` | List targets and health |
| 10 | Test alert manually | `curl -XPOST localhost:9093/api/v2/alerts -d '[{...}]'` (after port-forward) | Verify Alertmanager → Slack pipeline |

---

## Application Code Changes

To get Flask metrics into Prometheus, instrument the app.

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
- `flask_http_request_total{method,status,path}` — counter
- `flask_http_request_duration_seconds_bucket{...}` — histogram
- `flask_http_request_duration_seconds_count{...}` — count for histograms

### Test Gotcha

Don't call `metrics.info('flask_app_info', ...)` — it registers in the **global Prometheus registry** and fails with `ValueError: Duplicated timeseries in CollectorRegistry: flask_app_info` when tests create the app multiple times.

---

## Alert Rules

Defined in [helm/prometheus/values.yaml](../helm/prometheus/values.yaml) under `serverFiles.alerting_rules.yml`.

| Alert | Threshold | Severity | Method |
|-------|-----------|----------|--------|
| **HighCPUUsage** | CPU > 80% for 5m | warning | USE — Utilization |
| **HighDiskUsage** | Disk > 85% for 5m | warning | USE — Utilization |
| **HighRequestRate** | Flask req/s > 100 for 5m | warning | RED — Rate |
| **ErrorRateSpike** | 5xx > 5% in 10m | critical | RED — Errors |
| **HighP99Latency** | p99 > 1s for 5m | warning | RED — Duration |
| **VaultPodRestarted** | Vault restart in 5m | critical | Reliability |
| **ArgoCDServerRestarted** | ArgoCD restart in 5m | critical | Reliability |
| **PostgresPodRestarted** | Postgres restart in 5m | critical | Reliability |
| **EndpointDown** | Blackbox probe fails for 2m | critical | Synthetic |
| **HighEndpointLatency** | Probe duration > 1s for 5m | warning | Synthetic |

### Alert Anatomy

```yaml
- alert: ErrorRateSpike
  expr: sum(rate(flask_http_request_total{status=~"5.."}[10m]))
        / sum(rate(flask_http_request_total[10m])) > 0.05
  for: 5m                       # ← must be true for 5 min before firing (avoid flapping)
  labels:
    severity: critical          # ← used for routing in Alertmanager
  annotations:
    summary: "Error rate spike on Flask API"
    description: "5xx error rate exceeded 5% in last 10 minutes"
```

### Alertmanager Routing

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 10s              # batch within 10s of first alert
  group_interval: 5m           # batch new alerts within an existing group every 5m
  repeat_interval: 12h         # re-fire if still active
  receiver: 'slack-notifications'
```

---

## Grafana Dashboards

Pre-loaded via [helm/grafana/values.yaml](../helm/grafana/values.yaml) using `gnetId` (from grafana.com/dashboards):

| ID | Name | Datasource | Description |
|----|------|-----------|-------------|
| 1860 | Node Exporter Full | Prometheus | Comprehensive node metrics (CPU, mem, disk, network, FD) |
| 7249 | Kubernetes Cluster | Prometheus | Cluster overview (pods, restarts, CPU/mem) |
| 9628 | PostgreSQL Database | Prometheus | DB metrics (connections, queries, table sizes) |
| 7587 | Prometheus Blackbox Exporter | Prometheus | Endpoint uptime, HTTP status, probe duration |
| 13639 | Logs / App | Loki | Application log search |

### Building Custom Dashboards

For production:
1. Build dashboards in Grafana UI (drag/drop, edit panels)
2. Export as JSON (Settings → JSON Model)
3. Commit JSON to Git under `dashboards/`
4. Reference from values.yaml or use a sidecar to load on startup
5. Avoid clicking "save" in production Grafana — all changes via Git

---

## Slack Integration

| Step | Description |
|------|-------------|
| 1 | Create Slack app at `api.slack.com/apps` → "Create New App" → "From scratch" |
| 2 | Features → Incoming Webhooks → Activate → Add New Webhook to Workspace → pick channel |
| 3 | Copy webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`) |
| 4 | Create K8s secret (NOT in Git!): `kubectl create secret generic alertmanager-slack-webhook --from-literal=slack_url=<URL> -n observability` |
| 5 | Alertmanager values reference: `slack_api_url_file: /etc/alertmanager/secrets/slack_url` |
| 6 | Mount via `extraSecretMounts` in chart values |

### Why `slack_api_url_file` and Not `slack_api_url`?

GitHub Push Protection scans for Slack webhooks and blocks pushes containing them. Even if you bypass once, the URL ends up in git history forever. Using a K8s secret + file mount keeps the URL out of Git entirely.

### Test the Pipeline

```bash
kubectl port-forward -n observability svc/prometheus-alertmanager 9093:9093 &
sleep 2
curl -XPOST http://localhost:9093/api/v2/alerts -H "Content-Type: application/json" -d '[{
  "labels": {"alertname":"TestAlert","severity":"warning","instance":"manual-test"},
  "annotations": {"summary":"Test alert","description":"Manual test"}
}]'
```

Should land in Slack within seconds.

---

## Verification

### 1. Prometheus Targets — All Up

In Grafana → Explore → Prometheus, run:
```promql
up
```

Expected: `1` for every job (`flask-api`, `postgres-exporter`, `blackbox-http`, `kubernetes-nodes`, etc.)

### 2. Flask App Metrics

```promql
flask_http_request_total
```

Should return one series per pod with `method`, `status` labels.

### 3. Loki Logs

In Grafana → Explore → Loki:
```logql
{namespace="student-api"}
```

Streams Flask app logs in real-time.

### 4. Slack

Test alert via curl (above) → check `#alerts` channel.

---

## Commands Reference

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Port-forward Grafana | `kubectl port-forward -n observability svc/grafana 3000:80` | Local UI access |
| 2 | Port-forward Prometheus | `kubectl port-forward -n observability svc/prometheus-server 9090:9090` | Direct PromQL access |
| 3 | Port-forward Alertmanager | `kubectl port-forward -n observability svc/prometheus-alertmanager 9093:9093` | Manage silences, view alerts |
| 4 | Get Grafana password | `kubectl get secret grafana -n observability -o jsonpath='{.data.admin-password}' \| base64 -d` | Initial admin login |
| 5 | List Prometheus targets | `kubectl exec -n observability deploy/prometheus-server -c prometheus-server -- wget -qO- http://localhost:9090/api/v1/targets` | Verify scraping |
| 6 | List active alerts | `kubectl exec -n observability prometheus-alertmanager-0 -- wget -qO- http://localhost:9093/api/v2/alerts` | See firing alerts |
| 7 | Reload Prometheus config | `curl -X POST http://localhost:9090/-/reload` (after port-forward, requires `--web.enable-lifecycle`) | Apply config without restart |
| 8 | Query Loki labels | `kubectl exec -n observability deploy/grafana -- wget -qO- "http://loki.observability.svc.cluster.local:3100/loki/api/v1/labels"` | Confirm Loki receiving logs |
| 9 | Trigger test alert | `curl -XPOST localhost:9093/api/v2/alerts -d '[{...}]'` | Verify Slack pipeline |
| 10 | Silence an alert | Alertmanager UI or `amtool silence add alertname=ErrorRateSpike` | Mute during maintenance |

---

## Useful Queries

### PromQL (Metrics)

| Query | What It Shows |
|-------|--------------|
| `up` | All scrape targets and their health (1 = up, 0 = down) |
| `up == 0` | Only DOWN targets |
| `flask_http_request_total` | Total Flask requests by route/method/status |
| `rate(flask_http_request_total[1m])` | Flask requests per second |
| `sum by (status) (rate(flask_http_request_total[5m]))` | Request rate grouped by status |
| `histogram_quantile(0.99, rate(flask_http_request_duration_seconds_bucket[5m]))` | p99 latency |
| `pg_database_size_bytes` | Postgres DB sizes |
| `pg_stat_database_xact_commit` | DB commit count |
| `probe_success` | Blackbox endpoint health (1/0) |
| `probe_duration_seconds` | Endpoint response time |
| `100 - (avg by(instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` | CPU usage % per node |
| `node_filesystem_avail_bytes / node_filesystem_size_bytes * 100` | Disk free % |
| `kube_pod_container_status_restarts_total` | Pod restart counts |
| `sum(kube_pod_container_status_running) by (namespace)` | Running pods per namespace |
| `time() - process_start_time_seconds` | Pod uptime |

### LogQL (Loki)

| Query | What It Shows |
|-------|--------------|
| `{namespace="student-api"}` | All Flask app logs |
| `{app="flask-api"} \|= "ERROR"` | Only error log lines |
| `{app="flask-api"} \|~ "students/[0-9]+"` | Logs matching student endpoint regex |
| `count_over_time({app="flask-api"} \|= "ERROR" [5m])` | Error count over 5 min |
| `rate({app="flask-api"} \|= "ERROR" [1m])` | Error rate per second |
| `sum by (level) (count_over_time({app="flask-api"} \| json [5m]))` | Group log counts by level |

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | Prometheus pod CrashLoopBackOff: `permission denied: /data/queries.active` | hostpath provisioner doesn't apply `fsGroup` chown to existing PV directory | SSH to node and chown: `minikube ssh -n minikube-m03 "sudo chown -R 65534:65534 /var/hostpath-provisioner/observability/prometheus-server"` |
| 2 | Loki pod CrashLoopBackOff: `mkdir /var/loki/rules: permission denied` | Same | `chown -R 10001:10001 /var/hostpath-provisioner/observability/storage-loki-0` |
| 3 | Alertmanager: `unsupported scheme "" for URL` | `${SLACK_WEBHOOK_URL}` placeholder in config wasn't substituted | Use real URL OR move to `slack_api_url_file` reading from K8s secret |
| 4 | Alertmanager: `field not declared in schema (fsGroup)` | Schema validation: `fsGroup` is pod-level, not container-level | Use `podSecurityContext` instead of `securityContext` for fsGroup |
| 5 | postgres-exporter: `secret "postgres-secret" not found` | Secret only exists in `student-api` namespace | Add ESO ExternalSecret to also create it in `observability` ns |
| 6 | postgres-exporter: `expected string; got float64` | Chart's helper template expects `port` as string | `port: "5432"` (quoted) instead of `port: 5432` |
| 7 | Prometheus: custom scrape configs not appearing in config | `extraScrapeConfigs` was nested under `server:` but is a top-level field | Move `extraScrapeConfigs` to root level of values.yaml |
| 8 | Prometheus: `flask-api 404 NOT FOUND` on /metrics | App didn't expose Prometheus metrics | Add `prometheus-flask-exporter` to requirements.txt + `PrometheusMetrics(app)` to __init__.py |
| 9 | Tests fail: `Duplicated timeseries in CollectorRegistry: flask_app_info` | `metrics.info()` registers in global registry; tests create app multiple times | Drop `metrics.info()` line — base `PrometheusMetrics(app)` is sufficient |
| 10 | Grafana: `Post .../api/v1/query_range: i/o timeout` | Datasource URL missing port (defaulted to 80, Prometheus is on 9090) | URL must include `:9090` |
| 11 | EndpointDown alert firing for ArgoCD | ArgoCD redirects HTTP→HTTPS (returns 307); blackbox only accepted 200/201 | Update blackbox `valid_status_codes: [200, 201, 301, 302, 307, 308]` |
| 12 | GitHub Push Protection: "Push cannot contain secrets" | Slack webhook URL committed to values.yaml | Move webhook to K8s Secret + use Alertmanager's `slack_api_url_file`; rewrite history |
| 13 | Promtail pods 0/1 ready on some nodes | Readiness probe fails because no `student-api` pods on those nodes (no logs to ship) | Expected — harmless. Promtail still functional. |
| 14 | Loki dashboard "no data" but Explore works | Dashboard 13639 expects different label names than what Promtail ships | Use Explore for ad-hoc queries; replace dashboard if needed |
| 15 | Prometheus disk filling fast | High retention OR high cardinality labels | Reduce retention; remove high-cardinality labels (e.g., user_id); use recording rules |
| 16 | Alertmanager not sending to Slack | Wrong webhook URL OR misformatted config | Check `kubectl logs prometheus-alertmanager-0`; test webhook with curl directly |
| 17 | Grafana data source error: `tls: bad certificate` | Self-signed certs OR expired certs | Disable TLS verification (dev only) OR mount proper CA cert |
| 18 | High Prometheus memory usage | Too many time series (cardinality explosion) | Identify with `topk(10, count by(__name__)({__name__=~".+"}))`; remove offending metrics or labels |

---

## Interview Q&A

### Concepts

| Q | A |
|---|---|
| **Three pillars of observability?** | Metrics, Logs, Traces. Metrics = numerical time series. Logs = text events. Traces = request flow across services. |
| **Monitoring vs Observability?** | Monitoring = checking known metrics for known failure modes. Observability = ability to debug **unknown** failure modes from system outputs. Monitoring is a subset. |
| **USE vs RED method?** | USE for **resources** (Utilization, Saturation, Errors). RED for **services** (Rate, Errors, Duration). Use both. |
| **What are the Four Golden Signals?** | Latency, Traffic, Errors, Saturation. Google SRE Book. Combination of USE + RED. |
| **What's the difference between SLI, SLO, SLA?** | SLI = a metric (e.g., 99.9% requests succeed). SLO = a target on that metric (99.9% success/month). SLA = a contract with consequences if SLO is breached. |
| **What's an error budget?** | (1 - SLO) — the amount of allowed unreliability. E.g., 99.9% SLO = 43 min downtime/month error budget. Used to balance reliability vs feature velocity. |

### Prometheus

| Q | A |
|---|---|
| **What is Prometheus?** | A pull-based time-series metrics system. Scrapes `/metrics` endpoints, stores in TSDB, exposes PromQL for queries. |
| **Pull vs push for metrics?** | Pull (Prometheus default) = simpler service discovery, target health visible (target down = `up=0`). Push (statsd, Datadog) = better for short-lived jobs (push gateway exists for this). |
| **What's a Prometheus exporter?** | A small program that exposes app/service metrics in Prometheus format. Examples: node-exporter, postgres-exporter, blackbox-exporter, JMX exporter. |
| **What's a ServiceMonitor?** | A CRD from Prometheus Operator that auto-generates scrape configs for K8s Services. We used static `extraScrapeConfigs` instead (no operator). |
| **Counter vs Gauge vs Histogram?** | Counter = monotonically increasing (e.g., total requests). Gauge = up/down (e.g., current memory). Histogram = bucketed counts (e.g., latency distribution). |
| **What's a recording rule?** | Pre-computed PromQL expressions (`record:` rules in YAML). Speeds up dashboards by caching expensive queries. |
| **What's cardinality?** | Number of unique label value combinations. High cardinality (user_id label) = millions of time series = OOM. Avoid high-cardinality labels. |
| **How do you scale Prometheus?** | Federation (HA pairs scrape same targets), Thanos / Mimir for long-term storage and global query, sharding by team/service. |
| **How does Alertmanager dedupe alerts?** | Groups by labels (`group_by`), waits `group_wait` for similar alerts, then sends together. Re-fires every `repeat_interval` if still firing. |

### Loki

| Q | A |
|---|---|
| **What is Loki?** | A horizontally-scalable log aggregation system. Like Prometheus, but for logs. Cheap because it indexes only labels (not log content). |
| **Loki vs ELK (Elasticsearch)?** | Loki indexes only metadata (labels) — much cheaper at scale, simpler. ELK indexes everything — more flexible, more costly. |
| **What is Promtail?** | Log shipper for Loki. Tails log files, attaches labels, pushes to Loki. Runs as DaemonSet. |
| **Promtail vs Fluentd vs Fluent Bit?** | Promtail = purpose-built for Loki, simple. Fluentd/Fluent Bit = general-purpose log forwarders, more outputs supported. |
| **What's LogQL?** | Loki's query language. Similar syntax to PromQL. Filter by labels (`{app="flask"}`), grep (`\|= "ERROR"`), regex (`\|~ "..."`), parse JSON, extract metrics. |

### Grafana

| Q | A |
|---|---|
| **What is Grafana?** | Visualization platform. Pulls from data sources (Prometheus, Loki, Elasticsearch, etc.) and renders dashboards. |
| **How are dashboards versioned?** | Export as JSON, commit to Git. Or use Grafana's API + Terraform provider. Or use `grizzly` for GitOps-driven dashboards. |
| **Grafana datasource for Prometheus — what's needed?** | Type: prometheus. URL: `http://prometheus-server.observability.svc.cluster.local:9090` (note: must include port). Access: proxy. |
| **How to alert from Grafana vs Alertmanager?** | Grafana 9+ has unified alerting (handles both). Many teams still use Alertmanager (Prometheus-side) for alert routing because it's more mature for grouping/routing. |

### Real Production Scenarios

| Q | A |
|---|---|
| **Prometheus is OOMKilled. What do you check?** | High cardinality labels (`topk(10, count by(__name__)({__name__=~".+"}))`); too many series; retention too long. Fix: drop bad labels, reduce retention, scale Prometheus or move to Thanos. |
| **An alert fires constantly but the issue is intermittent.** | Tighten the `for:` duration (give time before firing), add hysteresis (different thresholds for fire/resolve). |
| **You need to alert when a Kafka consumer group lag > 10000.** | Use `prometheus-kafka-exporter`; alert on `kafka_consumergroup_lag > 10000`. For autoscaling: KEDA with kafka scaler. |
| **A dashboard is slow to load.** | Likely expensive query. Solutions: shorter time range, recording rule, downsampling, smaller step. |
| **How do you debug "the application is slow" with no specifics?** | (1) RED metrics — what's the latency p99 trend? (2) Logs around the timeframe. (3) Traces if available — where does time go? (4) Saturation — CPU, memory, DB connections. |
| **How do you reduce false positive alerts?** | Tune thresholds based on actual production data. Use `for:` to require sustained breach. Use multi-window multi-burn-rate alerts (Google SRE Book). |
| **How do you handle alert fatigue?** | Aggregate non-critical alerts into a daily digest. Critical-only to PagerDuty. Quarterly alert review — kill ones never acted on. |
| **How do you observe a microservices architecture?** | Distributed tracing (Jaeger/Tempo + OpenTelemetry SDK in apps). Service mesh (Istio) for automatic mTLS + telemetry. Per-service RED metrics. |

---

## STAR Stories

### Story 1: "Tell me about a time you debugged Prometheus permission errors."

**Situation:** After deploying Prometheus to minikube via ArgoCD, the pod was in CrashLoopBackOff with `permission denied: /data/queries.active`.

**Task:** Get Prometheus running without disabling its security context.

**Action:**
1. Inspected pod spec — `securityContext: { runAsUser: 65534, fsGroup: 65534 }` was set.
2. Confirmed pod's `securityContext` was applied: `kubectl get pod -o yaml`.
3. Realized **minikube's hostpath provisioner doesn't honor `fsGroup` chown** for newly-created PVs (works in cloud with EBS/GCE PD).
4. SSHed into the node: `minikube ssh -n minikube-m03`.
5. `sudo ls -la /var/hostpath-provisioner/observability/` — directory was owned by root.
6. `sudo chown -R 65534:65534 /var/hostpath-provisioner/observability/prometheus-server`.
7. Killed the pod; on restart, Prometheus came up cleanly.

**Result:** Prometheus running. Same pattern applied to Loki and Alertmanager (different UIDs).

**Takeaway:** `fsGroup` is a portable security control in cloud K8s but unreliable on local provisioners. For full portability, use an init container that runs as root and chowns the directory.

---

### Story 2: "Tell me about a time GitHub blocked a push because of a secret."

**Situation:** I committed a Slack webhook URL to `helm/prometheus/values.yaml` so Alertmanager could send to #alerts. On `git push`, GitHub rejected with "Push cannot contain secrets."

**Task:** Get the change in without leaking the webhook to Git history (Slack also auto-revoked the leaked webhook).

**Action:**
1. Read GitHub's error — offered a "bypass" URL but the secret would still land in history forever.
2. Decision: rewrite history so the webhook never lands in main.
3. Squashed two commits (the leak + the cleanup) using `git reset --soft HEAD~2 && git commit -m "..."`.
4. Re-architected:
   - Created a K8s Secret out-of-band: `kubectl create secret generic alertmanager-slack-webhook --from-literal=slack_url=<URL> -n observability`
   - In Alertmanager values: `slack_api_url_file: /etc/alertmanager/secrets/slack_url`
   - Mounted via `extraSecretMounts`
5. Generated a fresh webhook URL in Slack; stored only in K8s secret.

**Result:** Push succeeded with no secret in Git. Pattern documented for the team: "Secrets go in K8s Secrets / Vault / SSM — never values.yaml."

**Takeaway:** Push Protection caught a real mistake. Architect secrets out of git from day one. If a secret leaks, **rotate immediately** — assume it's compromised even if "only for a moment."

---

### Story 3: "Tell me about an alert that turned out to be a true positive."

**Situation:** `EndpointDown` alert fired in Slack: `http://argocd-server.argocd.svc.cluster.local is down`. ArgoCD UI was reachable from my browser, so I almost dismissed it.

**Task:** Validate whether ArgoCD was actually broken.

**Action:**
1. Checked the blackbox exporter probe URL — yes, it was the in-cluster ArgoCD service.
2. Curled it from a debug pod: `kubectl run debug --rm -it --image=nicolaka/netshoot -- curl -v http://argocd-server.argocd.svc.cluster.local`
3. Got `HTTP/1.1 307 Temporary Redirect` (ArgoCD redirects HTTP → HTTPS).
4. Checked our blackbox config — `valid_status_codes: [200, 201]`. 307 isn't in the list, so probe failed = alert fired.
5. The alert was technically correct (the probe failed) but the cause was config, not ArgoCD.
6. Updated blackbox config: `valid_status_codes: [200, 201, 301, 302, 307, 308]`.

**Result:** Alert resolved. No false alarms for redirect-using services. Documented the gotcha for future probes.

**Takeaway:** Synthetic monitoring catches what your scrape-only metrics miss — but verify the probe config matches the target's actual behavior. Always test alerts in staging before relying on them in prod.

---

### Story 4: "Tell me about implementing observability from scratch."

**Situation:** Joined a team where the only observability was `kubectl logs` and `kubectl top`. Production incidents took hours to diagnose.

**Task:** Stand up a full observability stack within a sprint, without over-engineering.

**Action:**
1. **Week 1:** Installed Prometheus + Grafana via Helm. Added node-exporter and kube-state-metrics. Pre-loaded 3 community dashboards.
2. **Week 2:** Instrumented Flask app with `prometheus-flask-exporter`. Set up RED metrics dashboard (rate, errors, duration p50/p95/p99).
3. **Week 3:** Added Loki + Promtail for log aggregation. Filtered logs to only the app namespaces (Promtail's relabel_configs).
4. **Week 4:** Defined 10 alert rules based on USE+RED methodology. Wired Alertmanager to Slack with sensible grouping (group by alertname + severity, repeat 12h).
5. **Week 5:** Onboarded the team — taught PromQL basics, demoed dashboards, set up runbooks for each alert.

**Result:** First incident afterward — DB connection pool exhaustion — diagnosed in 8 minutes from Slack alert → Grafana dashboard → Loki logs → root cause. Previously would have been a 2-hour outage.

**Takeaway:** Don't try to instrument everything at once. Start with the Four Golden Signals on your most critical service. Add custom metrics later. Most teams over-engineer observability before they need it.

---

## Production Hardening

| Area | Current | Production |
|------|---------|-----------|
| **Storage** | hostpath (lost on minikube delete) | EBS / persistent storage with snapshot-based backups |
| **Prometheus HA** | Single replica | Prometheus HA pair (2 replicas scrape same targets); Thanos / Mimir for long-term + global query |
| **Loki backend** | filesystem | S3 / GCS for object storage; Boltdb-shipper for index |
| **Retention** | 7 days | 30+ days for metrics, 90+ for logs (with downsampling) |
| **Alerting** | Slack only | Slack + PagerDuty (high severity) + email + dedup via Opsgenie |
| **TLS** | None | cert-manager + auto-renewed certs for all UIs |
| **Auth** | Grafana admin/admin | OIDC SSO (Google/Okta) for Grafana, Prometheus, Alertmanager |
| **Tracing** | Not implemented | Jaeger or Tempo + OpenTelemetry SDKs in apps |
| **Dashboards** | gnetId community dashboards | Custom dashboards in JSON, version-controlled in Git |
| **Recording rules** | None | Pre-aggregate expensive queries (`record:` rules) for fast dashboards |
| **Alert routing** | All to one Slack channel | Routes by team/severity/service via Alertmanager `routes` |
| **Webhook secrets** | K8s Secret (one-off kubectl create) | Vault + ESO sync (you already have ESO!) |
| **SLO tracking** | None | Define SLOs per service; use Sloth or Pyrra to generate burn-rate alerts |
| **Cardinality monitoring** | None | Alert on high cardinality (`prometheus_tsdb_symbol_table_size_bytes`) |
| **Synthetic monitoring** | Blackbox in-cluster | Pingdom / external probes for true uptime monitoring |

---

## Cloud Mapping

| Self-hosted | AWS | GCP | Azure |
|-------------|-----|-----|-------|
| Prometheus | Amazon Managed Prometheus (AMP) | GMP (Google Managed Prometheus) | Azure Monitor for Prometheus |
| Grafana | Amazon Managed Grafana (AMG) | Cloud Monitoring dashboards / Managed Grafana | Azure Managed Grafana |
| Loki | CloudWatch Logs (different model — indexed) | Cloud Logging | Azure Monitor Logs |
| Alertmanager | SNS + EventBridge | Cloud Monitoring alerts → Pub/Sub | Azure Monitor alerts |
| Jaeger / Tempo | AWS X-Ray | Cloud Trace | Azure Application Insights |
| Synthetic probes | CloudWatch Synthetics | Cloud Monitoring uptime checks | Application Insights availability tests |
| node-exporter | CloudWatch Agent | Ops Agent | Azure Monitor Agent |

---

## Reference Links (Internal)

- Prometheus values: [helm/prometheus/values.yaml](../helm/prometheus/values.yaml)
- Grafana values: [helm/grafana/values.yaml](../helm/grafana/values.yaml)
- Loki values: [helm/loki/values.yaml](../helm/loki/values.yaml)
- Promtail values: [helm/promtail/values.yaml](../helm/promtail/values.yaml)
- Postgres exporter: [helm/postgres-exporter/values.yaml](../helm/postgres-exporter/values.yaml)
- Blackbox exporter: [helm/blackbox-exporter/values.yaml](../helm/blackbox-exporter/values.yaml)
- ArgoCD apps: [argocd/observability-*.yaml](../argocd/)
