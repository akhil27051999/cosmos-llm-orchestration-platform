# Observability Stack — Prometheus, Loki, Grafana (Kubernetes)

This repository documents a production-ready, cloud-native observability stack and recommended configuration for metrics and logs in Kubernetes.

- Metrics: Prometheus scrapes exporters (node-exporter, kube-state-metrics, postgres-exporter, blackbox-exporter).
- Logs: Promtail collects pod logs and ships to Loki.
- Visualization: Grafana uses Prometheus and Loki as data sources.

Goal: Provide an end-to-end, maintainable monitoring and logging flow so you can correlate metrics, traces and logs for faster debugging and SLA monitoring.

---

## Architecture (Conceptual)

Applications / Infra -> Exporters & Agents -> Prometheus / Loki -> Grafana

ASCII diagram:

```text
Application Logs        Kubernetes Objects        Infrastructure Nodes
      |                        |                         |
      v                        v                         v
   Promtail             kube-state-metrics         node-exporter
      |                        |                         |
      ---------------------------------------------------
                             |
                             v
                           Loki
                             |
                             v
Grafana <-----------------> Prometheus
  ^                            ^
  |                            |
Blackbox Exporter        Postgres Exporter
  |                            |
HTTP Endpoints             PostgreSQL DB
(Student API, ArgoCD, Vault)
```

---

## Components & Responsibilities

- Prometheus
  - Scrapes exporter endpoints and stores time-series metrics.
  - Alerting rules (PrometheusRule) and PromQL queries.
- node-exporter
  - Node-level metrics (CPU, memory, disk, network).
- kube-state-metrics
  - Kubernetes object state metrics (pods, deployments, replica counts).
- postgres-exporter
  - PostgreSQL metrics: queries, connections, locks, replication.
- blackbox-exporter
  - Probes external endpoints: HTTP, TCP, ICMP; measures latency & availability.
- Grafana
  - Visualization layer (dashboards for metrics & logs).
  - Alerting integrations (Alertmanager, Email, Slack, PagerDuty).
- Loki
  - Indexless log store; stores logs by labels; supports object storage backends.
- Promtail
  - DaemonSet, tails pod logs and forwards to Loki, attaches labels.

---

## Data Flow (Concise)

- Metrics:
  - exporters → Prometheus → Grafana
- Logs:
  - Promtail (DaemonSet) → Loki → Grafana
- Synthetic / Uptime:
  - Blackbox Exporter → Prometheus → Grafana

---

## Quickstart (Kubernetes / Helm, high-level)

1. Install Prometheus (Prometheus Operator / kube-prometheus-stack recommended):
   - Helm chart: prometheus-community/kube-prometheus-stack
   - This includes ServiceMonitors, Prometheus, Alertmanager, Grafana (optional).

2. Deploy exporters:
   - node-exporter as DaemonSet (often included by kube-prometheus-stack).
   - kube-state-metrics Deployment.
   - postgres-exporter (Deployment or sidecar) with secret for DB credentials.
   - blackbox-exporter Deployment with probe module configs.

3. Deploy Loki + Promtail:
   - Install Grafana Loki chart (grafana/loki-stack) or separate charts.
   - Configure Promtail as DaemonSet to read /var/log/pods and attach pod metadata.

4. Configure Grafana:
   - Add Prometheus and Loki data sources.
   - Import dashboards:
     - Node Exporter Full
     - kube-state-metrics overview
     - PostgreSQL Overview
     - Blackbox Exporter (Uptime / Latency)

5. Configure persistence & storage:
   - Prometheus: persistentVolumeClaims (size depends on retention and scrape rate).
   - Loki: object storage (S3/GCS) recommended for long-term retention; use chunks/boltdb-shipper or cassandra for scale.

---

## Example Snippets

Prometheus scrape_configs (minimal illustrative example):

```yaml
scrape_configs:
  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - source_labels: [__meta_kubernetes_node_label_kubernetes_io_arch]
        regex: .*
        action: keep

  - job_name: 'kube-state-metrics'
    static_configs:
      - targets: ['kube-state-metrics.kube-system.svc.cluster.local:8080']

  - job_name: 'node-exporter'
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_label_app]
        regex: node-exporter
        action: keep

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter.monitoring.svc.cluster.local:9187']

  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://student-api.example.com/healthz
        - https://argocd.example.com/
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter.monitoring.svc.cluster.local:9115
```

Promtail sample pipeline config (very small example):

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /var/log/positions.yaml

clients:
  - url: http://loki.monitoring.svc.cluster.local:3100/loki/api/v1/push

scrape_configs:
  - job_name: kubernetes-pods
    pipeline_stages:
      - docker: {}
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
```

PrometheusRule alerts examples:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: critical-alerts
spec:
  groups:
    - name: instance-down
      rules:
        - alert: InstanceDown
          expr: up == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "{{ $labels.instance }} is down"
```

---

## Best Practices & Recommendations

- Use Prometheus Operator / kube-prometheus-stack for Kubernetes-native ServiceMonitor CRDs and easier management.
- Label everything consistently:
  - Metrics and logs should share service/pod labels to ease correlation in Grafana.
- Retention & Storage:
  - Prometheus: tune scrape interval and retention (e.g., 15d) according to storage costs.
  - Loki: use object storage for retention > weeks.
- Security:
  - TLS for Prometheus, Grafana, Loki endpoints where exposed.
  - RBAC + NetworkPolicies to restrict access to metrics endpoints and admin UIs.
  - Secrets in Kubernetes for DB credentials and exporters.
- Scaling:
  - Shard Prometheus for high cardinality / large clusters or use Thanos/Cortex for long-term, global view.
  - Use Loki Horizontal scaling patterns (index and ingesters) for high-volume logs.

---

## Dashboards & Useful Panels

- System (Node Exporter Full)
  - CPU, Memory, Disk, Network, Filesystem usage.
- Kubernetes Overview (kube-state-metrics)
  - Pod restarts, CrashLoopBackOff, deployment availability.
- Database (Postgres)
  - Connections, slow queries, locks, replication lag.
- Synthetic / Uptime (Blackbox)
  - Endpoint availability, response latency, SSL expiry.
- Logs
  - Error rate over time, searching by labels (namespace, pod, container).

---

## Troubleshooting

- No metrics showing in Grafana:
  - Check Prometheus targets page (/targets).
  - Verify scrape_config and ServiceMonitor selectors.
  - Check network policies and DNS resolution.
- Logs missing in Grafana:
  - Check promtail logs (DaemonSet) for errors connecting to Loki.
  - Ensure promtail has permission to read /var/log/containers and /var/log/pods.
  - Verify label mapping (namespace/pod) used in queries.
- High cardinality in Prometheus:
  - Identify problematic metrics (labels that vary per request).
  - Reduce label cardinality or route high-cardinality metrics to a separate system.

---

## Resource Sizing (Guideline)

- Small cluster (<= 20 nodes): a single Prometheus + 1 Loki with small PVCs may suffice.
- Medium (20–200 nodes): consider Prometheus remote_write to long-term store (Thanos/Cortex) and scale Loki.
- High cardinality apps: always offload long-term to Thanos/Cortex and use recording rules to pre-aggregate metrics.

---

## Next Steps & Enhancements

- Add Alertmanager and configure receivers (Slack, PagerDuty).
- Integrate tracing (Jaeger/Tempo) and link traces to logs + metrics.
- Add automated dashboard provisioning and Grafana playlists.
- Implement CI/CD for observability manifests (Helm values, Kustomize overlays).
- Add SLO/SLI definitions and SLO dashboards.

---

## References & Useful Links

- Prometheus: https://prometheus.io/
- Prometheus Operator / kube-prometheus-stack: https://github.com/prometheus-operator/kube-prometheus
- Grafana: https://grafana.com/
- Loki & Promtail: https://grafana.com/oss/loki/
- Blackbox Exporter: https://github.com/prometheus/blackbox_exporter
- PostgreSQL Exporter: https://github.com/prometheus-community/postgres_exporter
- kube-state-metrics: https://github.com/kubernetes/kube-state-metrics

---

If you'd like, I can:
- generate Helm values examples for kube-prometheus-stack + loki-stack,
- produce ServiceMonitor/PodMonitor YAMLs for this stack,
- or create recommended Grafana dashboards (JSON) for the Student API, Postgres and cluster health.
