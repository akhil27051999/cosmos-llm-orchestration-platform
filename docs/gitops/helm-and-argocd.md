# Helm - Kubernetes Package Manager

<img width="761" height="461" alt="Screenshot 2025-12-10 195411" src="https://github.com/user-attachments/assets/703b2009-05fe-4610-bd3f-e580565e60ae" />

### What is Helm?
Helm is the package manager for Kubernetes, often referred to as "the apt/yum/homebrew for K8s". It simplifies deploying and managing applications on Kubernetes clusters.

### Why Use Helm?
Problems Helm Solves:
- Complexity: K8s manifests can have 10+ YAML files per application
- Repetition: Same application across different environments
- Versioning: No built-in version tracking for deployments
- Dependencies: Manual management of dependent services
- Updates: Difficult to roll back deployments

### Helm Benefits:
```bash
# Without Helm
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml 
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# With Helm
helm install my-app ./my-chart
```

## Key Concepts
### 1. Charts
- Package containing all K8s resources needed to run an application

**Directory structure:**
```text
my-chart/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default configuration
├── templates/          # K8s manifest templates
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── charts/             # Sub-charts/dependencies
```

### 2. Releases
- Instance of a chart running in a K8s cluster
- Each helm install creates a new release
- Multiple releases of same chart can coexist

### 3. Repositories
- Collection of charts you can install
- Like package repositories (Docker Hub for charts)

## Basic Commands
### Installation & Setup
```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Common Operations
```bash
# Install a chart
helm install my-app bitnami/nginx

# Install from local chart
helm install my-app ./my-chart

# Upgrade release
helm upgrade my-app ./my-chart

# List releases
helm list

# Uninstall
helm uninstall my-app

# Check history
helm history my-app

# Rollback
helm rollback my-app 1
```

## Chart Structure Deep Dive
### Chart.yaml
```yaml
apiVersion: v2
name: my-app
description: A simple Flask application
type: application
version: 1.0.0
appVersion: "2.1.0"

dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
```

### values.yaml (Configuration)
```yaml
# Default values
replicaCount: 2

image:
  repository: nginx
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false

resources:
  limits:
    memory: 128Mi
    cpu: 500m
```

### Template Files (templates/deployment.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-deployment
  labels:
    app: {{ .Values.image.repository }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Values.image.repository }}
  template:
    metadata:
      labels:
        app: {{ .Values.image.repository }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: {{ .Values.service.port }}
```

## Template Engine Features
### Variables & Functions
```yaml
# Basic variable
name: {{ .Release.Name }}

# Default values
port: {{ .Values.service.port | default "80" }}

# Conditionals
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
{{- end }}

# Loops
{{- range .Values.envVars }}
- name: {{ .name }}
  value: {{ .value }}
{{- end }}

# Built-in functions
name: {{ .Release.Name | lower | replace " " "-" }}
```

### Flow Control
```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
{{- end }}
```

## Advanced Features
### Dependencies
```yaml
# Chart.yaml
dependencies:
  - name: postgresql
    version: "12.0.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled

# Download dependencies
helm dependency update
```

### Hooks (for jobs, migrations)
```yaml
# templates/migration-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-db-migration
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "0"
spec:
  template:
    spec:
      containers:
      - name: migration
        image: my-app:migrate
```

### Value Files for Environments
```bash
# Development
helm install my-app ./my-chart -f values-dev.yaml

# Production  
helm upgrade my-app ./my-chart -f values-prod.yaml

# Override specific values
helm install my-app ./my-chart --set replicaCount=3 --set image.tag=latest
```

## Best Practices
### 1. Chart Organization
```bash
my-chart/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-prod.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── _helpers.tpl    # Shared templates
│   └── tests/
│       └── test-connection.yaml
└── charts/             # Dependencies
```

### 2. Security
```bash
# Don't store secrets in values.yaml
# Use external secrets or Helm secrets plugin
helm plugin install https://github.com/jkroepke/helm-secrets

# Encrypt sensitive values
helm secrets enc values/secrets.yaml
```

### 3. Testing & Validation
```bash
# Lint chart
helm lint ./my-chart

# Dry-run installation
helm install my-app ./my-chart --dry-run --debug

# Template rendering test
helm template my-app ./my-chart

# Test installation
helm test my-app
```

## Deployment Commands
```bash
# Development
helm install flask-api ./helm/flask-api -n student-api -f values-dev.yaml

# Production
helm upgrade flask-api ./helm/flask-api -n student-api -f values-prod.yaml

# With custom values
helm install flask-api ./helm/flask-api \
  --set replicaCount=3 \
  --set image.tag="v2.1.0" \
  --set service.type=LoadBalancer
```

## Common Troubleshooting
### 1. Template Errors
```bash
# Debug template rendering
helm template my-app ./my-chart --debug

# Check specific value
helm get values my-app
```

### 2. Upgrade Issues
```bash
# Check history
helm history my-app

# Rollback
helm rollback my-app 1

# Force upgrade (if needed)
helm upgrade my-app ./my-chart --force
```

### 3. Dependency Issues
```bash
# Update dependencies
helm dependency update

# List dependencies
helm dependency list
```

### Summary
Helm makes Kubernetes deployments:
- Repeatable - Same chart works across environments
- Configurable - Values files for different configurations
- Versioned - Track changes and rollback easily
- Shareable - Charts can be packaged and distributed
- Standardized - Consistent structure across applications


# ArgoCD Comprehensive Documentation

## 1. Introduction to ArgoCD

### What is ArgoCD?
- ArgoCD is a declarative, GitOps continuous delivery tool for Kubernetes that automates deployment of applications based on manifests stored in a Git repository.

#### Key Features
- GitOps-based deployments - Git as single source of truth
- Automated sync from Git to Kubernetes
- Health checks and status reporting
- Multi-source support (Helm, Kustomize, plain YAML)
- Rollback and version tracking
- Web UI and CLI for management

### Why We Use ArgoCD
- Ensures cluster state matches Git repository
- Provides audit trail of deployments
- Enables easy rollbacks
- Automates application deployment
- Visualizes application status

## 2. Architecture Overview
```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repository│    │   ArgoCD        │    │   Kubernetes    │
│                 │    │   Server        │    │   Cluster       │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Application │◄┼────┼─┤ Application │◄┼────┼─┤ Deployments │ │
│ │ Manifests   │ │    │ │ Controller  │ │    │ │ Services    │ │
│ │ (Helm/YAML) │ │    │ └─────────────┘ │    │ │ Secrets     │ │
│ └─────────────┘ │    │                 │    │ └─────────────┘ │
│                 │    │ ┌─────────────┐ │    │                 │
│ ┌─────────────┐ │    │ │   Repo      │ │    │ ┌─────────────┐ │
│ │   Values    │◄┼────┼─┤   Server    │ │    │ │   Pods      │ │
│ │   Files     │ │    │ └─────────────┘ │    │ │ Services    │ │
│ └─────────────┘ │    └─────────────────┘    │ └─────────────┘ │
└─────────────────┘                           └─────────────────┘
```

### Core Components
- ArgoCD Server: API server and web UI
- Repository Server: Handles Git operations
- Application Controller: Monitors and syncs applications
- Redis: Caching and session storage

## 3. Installation Guide

### 3.1 Prerequisites
```bash
# Verify Kubernetes cluster
kubectl get nodes

# Verify kubectl access
kubectl auth can-i create deployments

# Required namespaces
kubectl create namespace argocd
```

### 3.2 Installation Methods

#### Method 1: Using kubectl (Official)
```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Verify installation
kubectl get pods -n argocd -w
```

### Method 2: Using Helm (Recommended)

```bash
# Add ArgoCD Helm repository
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Create values file
cat > argocd-values.yaml << EOF
server:
  service:
    type: LoadBalancer
  ingress:
    enabled: true
configs:
  params:
    server.insecure: true
EOF

# Install ArgoCD
helm install argocd argo/argo-cd -n argocd --create-namespace -f argocd-values.yaml
```

### 3.3 Accessing ArgoCD
**Port Forwarding**

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

**Access: https://localhost:8080**

#### Get Admin Password
```bash
# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Change password (recommended)
argocd account update-password --current-password <temp-password> --new-password <secure-password>
```

## 4. Application Configuration

### 4.1 Application YAML Structure
```yaml
# external-secrets-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: external-secrets
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/akhil27051999/Flask-REST-API.git
    targetRevision: dev
    path: helm/external-secrets
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: external-secrets
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### 4.2 Application Definitions for Our Stack
```yaml
# flask-api-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: flask-api
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/akhil27051999/Flask-REST-API.git
    targetRevision: dev
    path: helm/flask-api
  destination:
    server: https://kubernetes.default.svc
    namespace: student-api
  syncPolicy:
    automated:
      prune: true
      selfHeal: true

# postgres-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: postgres
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/akhil27051999/Flask-REST-API.git
    targetRevision: dev
    path: helm/postgres
  destination:
    server: https://kubernetes.default.svc
    namespace: student-api
  syncPolicy:
    automated:
      prune: true
      selfHeal: false  # Manual sync for database
```

### 4.3 Creating Applications
```bash
# Apply application definitions
kubectl apply -f external-secrets-app.yaml
kubectl apply -f flask-api-app.yaml
kubectl apply -f postgres-app.yaml

# Check application status
argocd app list
kubectl get applications -n argocd
```

## 5. Troubleshooting Guide

### 5.1 Common Issues and Solutions

#### Issue 1: Application Shows "Unknown" or "Error" Status
`Symptoms:`
- Dashboard shows "Failed to load data"
- Application status unknown

`Causes:`
- Network/API connectivity issues
- RBAC restrictions
- Dependent resources not ready

`Solutions:`
```bash
# Check ArgoCD pods
kubectl get pods -n argocd

# Check logs for errors
kubectl logs -n argocd deployment/argocd-server
kubectl logs -n argocd deployment/argocd-repo-server

# Verify dependent services
kubectl get pods -n external-secrets
kubectl get pods -n vault
```

#### Issue 2: Sync Fails

`Symptoms:`
- ArgoCD fails to sync application from Git

`Causes:`
- Incorrect Git repo URL or branch
- Path to Helm chart incorrect
- Missing values files

`Solutions:`
```bash
# Verify Git repo access
git ls-remote https://github.com/akhil27051999/Flask-REST-API.git

# Check application configuration
argocd app get external-secrets

# Manual sync with pruning
argocd app sync external-secrets --prune
```

#### Issue 3: ExternalSecrets Health Check Issues
`Symptoms:`
- ExternalSecrets app shows Error or Unknown
*Causes:`
- ESO operator pod issues
- Vault connectivity problems
- RBAC permission issues

`Solutions:`

```bash
# Check ESO operator
kubectl get pods -n external-secrets
kubectl logs -n external-secrets deployment/external-secrets-operator

# Verify Vault connectivity
kubectl exec -n vault -it <vault-pod> -- vault status

# Check ClusterSecretStore
kubectl get clustersecretstore vault-secretstore -o yaml
```

#### Issue 4: PushSecret Permission Errors
`Symptoms:` ESO logs show PushSecret forbidden errors
`Causes:`
- Service account lacks PushSecret permissions
- ESO tries to watch PushSecrets by default

`Solutions:`
```yaml
# Option 1: Add PushSecret permissions to ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: external-secrets-cluster-role
rules:
- apiGroups: ["external-secrets.io"]
  resources: ["secretstores", "clustersecretstores", "externalsecrets", "pushsecrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```
OR
```bash
# Option 2: Restart ESO pod (temporary fix)
kubectl delete pod -n external-secrets -l app.kubernetes.io/name=external-secrets
```

### 5.2 Diagnostic Commands
```bash
# Comprehensive health check
#!/bin/bash
echo "=== ArgoCD Pods Status ==="
kubectl get pods -n argocd

echo -e "\n=== Application Status ==="
argocd app list

echo -e "\n=== External Secrets Status ==="
kubectl get externalsecret -n student-api

echo -e "\n=== Secret Status ==="
kubectl get secret postgres-secret -n student-api

echo -e "\n=== Recent Logs ==="
kubectl logs -n external-secrets deployment/external-secrets-operator --tail=50
```

### 5.3 Vault Integration Troubleshooting
```bash
# Verify Vault secrets
kubectl exec -n vault -it vault-0 -- /bin/sh -c "
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'
vault kv get secret/studentdb
"

# Check Vault token secret
kubectl get secret vault-token -n external-secrets -o yaml

# Test Vault connectivity from ESO
kubectl exec -n external-secrets -it <eso-pod> -- curl -H "X-Vault-Token: root" http://vault.vault.svc.cluster.local:8200/v1/secret/data/studentdb
```

## 6. Best Practices

### 6.1 GitOps Principles

- Single Source of Truth: Git repository contains all configuration
- Automated Sync: Enable automated deployment with self-healing
- Immutable Infrastructure: Don't make manual changes to cluster

### 6.2 Application Management
```yaml
# Recommended sync policy
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
  retry:
    limit: 3
    backoff:
      duration: 5s
```

### 6.3 Security Practices
```bash
# Change default admin password
argocd account update-password

# Use RBAC for team access
kubectl apply -f - << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    p, role:readonly, applications, get, */*, allow
    g, developers, role:readonly
EOF
```

### 6.4 Monitoring and Alerting
```bash
# Set up application health checks
argocd app set external-secrets --health-check-timeout 3m

# Monitor sync status
argocd app wait external-secrets --health --timeout 600
```

## 7. Command Reference
### 7.1 ArgoCD CLI Commands
```bash
# Login to ArgoCD
argocd login <server> --username admin --password <password>

# List applications
argocd app list

# Get application details
argocd app get <app-name>

# Sync application
argocd app sync <app-name>

# Sync with pruning
argocd app sync <app-name> --prune

# Refresh application
argocd app refresh <app-name>

# Check application health
argocd app health <app-name>

# View application logs
argocd app logs <app-name>

# Delete application
argocd app delete <app-name>
```

### 7.2 Kubernetes Commands
```bash
# Check all resources in namespaces
kubectl get all -n student-api
kubectl get all -n external-secrets
kubectl get all -n vault

# Check specific resources
kubectl get externalsecret -n student-api
kubectl get clustersecretstore
kubectl get secret -n student-api

# Debug pods
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl logs -f <pod-name> -n <namespace>

# Check events
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp
```

### 7.3 Helm Commands
```bash
# For manual troubleshooting
helm list -A
helm status <release-name> -n <namespace>
helm get values <release-name> -n <namespace>
helm upgrade <release-name> <chart> -n <namespace> -f values.yaml
```

## 8. Complete Deployment Workflow

### 8.1 Initial Setup
```bash
# 1. Install ArgoCD
helm install argocd argo/argo-cd -n argocd --create-namespace -f argocd-values.yaml

# 2. Access ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# 3. Login and get password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# 4. Create applications
kubectl apply -f applications/
```

### 8.2 Daily Operations
```bash
# Check overall status
argocd app list

# Monitor specific application
argocd app get flask-api

# Force sync if needed
argocd app sync external-secrets

# Check resource utilization
kubectl top pods -A
```

## 9. Conclusion

- ArgoCD provides a robust GitOps solution for managing Kubernetes applications. By following this documentation, you can:
  - Install and configure ArgoCD properly
  - Deploy applications using Git as source of truth
  - Troubleshoot common issues effectively
  - Maintain best practices for security and operations
  - Monitor application health and sync status
