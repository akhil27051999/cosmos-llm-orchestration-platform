# Kubernetes Cluster Deployment Documentation

https://github.com/user-attachments/assets/933054ea-6916-418f-a6e1-1a05f6b3587a

## Milestone Expectation

### Problem Statement
- We need to spin up a three-node Kubernetes cluster using Minikube on your local. Going forward we will treat this Kubernetes cluster as our production cluster.
- Out of these three nodes
  - Node A will be used by our application.
  - Node B will be used for running database.
  - Node C will be used for running our dependent service such as observability stack, vault for storing secrets, etc.

### Expectations
The following expectations should be met to complete this milestone.
- Three node Kubernetes cluster using Minikube should be spun up.
- Appropriate node labels should be added to these three nodes.
- Ex:
  - Node A: type=application
  - Node B: type=database
  - Node C: type=dependent_services

## Objective
Deploy a production-ready 3-node Kubernetes cluster using Minikube with specialized node roles for application segregation.

### Implementation Summary

#### Cluster Architecture

| **Node Name**    | **Role**      | **Labels**                | **Purpose**                                    |
| ---------------- | ------------- | ------------------------- | ---------------------------------------------- |
| **minikube**     | Control Plane | `type=application`        | Hosts main application workloads               |
| **minikube-m02** | Worker        | `type=database`           | Dedicated to database services                 |
| **minikube-m03** | Worker        | `type=dependent_services` | Runs monitoring, secrets, and support services |


### Resource Allocation
- CPU: 4 cores per node
- Memory: 15.4GB per node
- Storage: 47GB per node
- File Descriptors: 1,048,576 per container

## Technical Implementation

### 1. Cluster Creation
```bash
minikube start --memory=4096 --cpus=2 --disk-size=20g --driver=docker --nodes=3
```

#### Configuration Breakdown:
- Driver: Docker (container-based nodes)
- Nodes: 3-node cluster (1 control plane + 2 workers)
- Resources: Balanced allocation for development/production parity

### 2. Node Labeling Strategy
```bash
kubectl label node minikube type=application
kubectl label node minikube-m02 type=database
kubectl label node minikube-m03 type=dependent_services
```

#### Label Purpose:
- Application Node: Web services, APIs, microservices
- Database Node: PostgreSQL, Redis, persistent data stores
- Dependent Services: Monitoring, logging, secrets management

### 3. System Verification
Health Checks Performed:
- All 3 nodes running (Control Plane + 2 Workers)
- 12/12 system pods healthy across all namespaces
- Network components (kube-proxy, CoreDNS) operational
- Resource allocation properly configured
- File descriptor limits optimized (1M per container)

## Critical Configuration Details

### File Descriptor Management

#### Issue Identified & Resolved:
- Problem: Container FD limit initially showed 1024 (misleading shell limit)
- Root Cause: Shell ulimit command doesn't reflect actual container limits
- Solution: Verified via /proc/1/limits showing 1,048,576 FDs
- Current Usage: 3,424 FDs (0.3% utilization) - Healthy

#### Network Configuration
- CNI: Kindnet (Container Network Interface)
- Service Proxy: kube-proxy running on all nodes
- DNS: CoreDNS operational for service discovery
- Network Policies: Ready for application-specific rules

#### Storage Provisioning
- Default StorageClass: Enabled
- Dynamic Provisioning: Available via storage-provisioner
- Volume Support: Ready for persistent volume claims

#### Capacity Planning & Scaling

| **Resource**         | **Utilization** | **Capacity**  | **Status**      |
| -------------------- | --------------- | ------------- | --------------- |
| **CPU**              | ~5%             | 4 cores/node  | ✅ Underutilized |
| **Memory**           | ~10%            | 15.4 GB/node  | ✅ Healthy       |
| **Storage**          | ~10%            | 47 GB/node    | ✅ Ample         |
| **File Descriptors** | 0.3%            | 1 M/container | ✅ Optimized     |

#### Estimated Workload Capacity

| **Workload Type**    | **Capacity/Node** | **Total Cluster** |
| -------------------- | ----------------- | ----------------- |
| **Microservices**    | 50–100 pods       | 150–300 pods      |
| **Databases**        | 2–3 instances     | 6–9 instances     |
| **Monitoring Stack** | 10–15 pods        | 30–45 pods        |

## Troubleshooting & Monitoring

### Essential Health Checks
```bash
# Cluster status
minikube status
kubectl get nodes -o wide

# System pods health
kubectl get pods -A --sort-by=.metadata.namespace

# Resource utilization
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocatable"
```

### Common Issue Resolution

#### 1. "Too many open files"
- Verify: kubectl exec <pod> -- cat /proc/1/limits | grep "Max open files"
- Expected: 1048576

#### 2. Pod scheduling failures
- Check: kubectl describe node | grep -A 10 "Allocated resources"
- Verify node labels and resource requests

#### 3. Network connectivity issues
- Verify kube-proxy: kubectl get pods -n kube-system -l k8s-app=kube-proxy
- Check CoreDNS: kubectl get pods -n kube-system -l k8s-app=kube-dns

## Application Deployment Ready

### Node Affinity Examples
```yaml
# Database deployment to database node
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: type
          operator: In
          values:
          - database

# Application deployment to application node  
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: type
          operator: In
          values:
          - application
```

### Namespace Strategy
- Development: Application testing
- Production: Live workloads
- Monitoring: Observability stack
- Database: Persistent data services

###  Final Status & Next Steps
#### Current Cluster State
- Infrastructure: 3-node cluster operational
- Networking: All components healthy
- Storage: Dynamic provisioning enabled
- Security: RBAC ready for policy implementation
- Monitoring: Ready for observability stack deployment

### Ready for Application Deployment
**The cluster is now prepared for:**
- Database Deployment → type=database node
- Application Services → type=application node
- Supporting Services → type=dependent_services node
- Load Balancing → Ingress controller setup
- Monitoring → Prometheus/Grafana deployment

### Production Considerations
- Implement proper resource requests/limits
- Configure liveness/readiness probes
- Set up automated backups for database node
- Implement network policies for service isolation
- Configure monitoring and alerting

# HashiCorp Vault on Kubernetes - Documentation

### Overview

#### Purpose
Deploy HashiCorp Vault as a secure secrets management solution on Kubernetes, specifically targeting the dependent_services node for isolation and persistence.

#### Key Features
- Persistent storage using Kubernetes PVC
- Secure non-root container execution
- Proper node segregation on minikube-m03
- External Secrets Operator integration ready
- Development and production-ready configuration

### Architecture

#### Component Diagram
```txt
┌─────────────────┐     ┌──────────────────┐    ┌────────────────────┐
│   Application   │     │   External       │    │   HashiCorp Vault  │
│     Pods        │───▶│   Secrets        │───▶│   (minikube-m03)   │
│                 │     │   Operator       │    │                    │
└─────────────────┘     └──────────────────┘    └────────────────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                          ┌──────────────┐
                          │ Kubernetes   │
                          │   Secrets    │
                          └──────────────┘
```
### Node Placement Strategy

| **Component**    | **Node**     | **Label**                 | **Purpose**                   |
| ---------------- | ------------ | ------------------------- | ----------------------------- |
| **Vault**        | minikube-m03 | `type=dependent_services` | Secrets management & security |
| **Applications** | minikube     | `type=application`        | Business logic services       |
| **Database**     | minikube-m02 | `type=database`           | Persistent data storage       |

### Prerequisites

#### System Requirements
- 3-node Minikube cluster running
- kubectl configured and accessible
- StorageClass standard available
- Node labels properly applied

### Cluster Verification

```bash
# Verify cluster nodes
kubectl get nodes --show-labels

# Verify storage class
kubectl get storageclass

# Verify node resources
kubectl describe node minikube-m03
```

## Installation Steps

### 1. Vault Deployment Manifest
The deployment uses a comprehensive YAML configuration including:

**Components Created:**

- Namespace: vault for isolation
- PersistentVolumeClaim: 0.5Gi storage
- ConfigMap: Vault server configuration
- ServiceAccount: For Kubernetes auth
- Service: ClusterIP for internal access
- Deployment: Vault server with init containers

### 2. Deployment Execution

```bash
# Apply the Vault configuration
kubectl apply -f vault.yaml

# Verify all components
kubectl get all -n vault
kubectl get pvc -n vault
```

### 3. Expected Output
```bash
NAMESPACE     NAME                         READY   STATUS    RESTARTS   AGE
vault         pod/vault-xxxxxxxxxx-xxxxx   1/1     Running   0          2m

NAMESPACE     NAME                    TYPE        CLUSTER-IP      PORT(S)    AGE
vault         service/vault-service   ClusterIP   10.96.xxx.xxx   8200/TCP   2m

NAMESPACE     NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
vault         deployment.apps/vault   1/1     1            1           2m

NAMESPACE     NAME                              STATUS   VOLUME   CAPACITY
vault         persistentvolumeclaim/vault-pvc   Bound    pvc-xxx  512Mi
```

## Configuration Details

### Vault Server Configuration (vault.hcl)

```hcl
ui = true
disable_mlock = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://vault-service.vault.svc.cluster.local:8200"
cluster_addr = "https://vault-service.vault.svc.cluster.local:8201"
```

#### Key Configuration Parameters

| **Parameter**     | **Value**              | **Purpose**                                      |
| ----------------- | ---------------------- | ------------------------------------------------ |
| **disable_mlock** | `true`                 | Required in containerized environments           |
| **storage**       | `file`                 | Uses filesystem with persistent volume           |
| **path**          | `/vault/data`          | Data persistence location                        |
| **tls_disable**   | `1`                    | HTTP for development (enable TLS for production) |
| **api_addr**      | *Internal service DNS* | For cluster communication                        |

### Security Context
```yaml
securityContext:
  runAsUser: 100      # Non-root user
  runAsGroup: 1000    # Specific GID
  fsGroup: 1000       # Filesystem group
```

### Init Container for permission

```yaml
initContainers:
- name: init-permissions
  image: busybox
  command: ['sh', '-c', 'mkdir -p /vault/data && chown 100:1000 /vault/data && chmod 755 /vault/data']
  securityContext:
    runAsUser: 0      # Run as root for permission setup
```

## Initialization & Unsealing

### 1. Vault Initialization
```bash
# Access Vault pod
kubectl exec -n vault -it deployment/vault -- /bin/sh

# Initialize Vault
vault operator init
```

#### Expected Output (SAVE SECURELY):

```text
Unseal Key 1: WcZ+hG6vGm9AjCa5NBtLQoe+xy+RVUG2wYsnSVFA8lPn
Unseal Key 2: mAqSlqkAJLTCChz5Izp2KYyLaBT2WzkChCy+11Y9OTmb
Unseal Key 3: YC8pqKprCwTIhCbQbxWtwmw0WN/Txm+ucovHhA9TKbKj
Unseal Key 4: 8p/7Ctq8bOi7/RpvYPz0HvY8VfRh31meif5Wrr5gKyha
Unseal Key 5: 7uoJjqttvrrqihN7tuckOTUlbgQXqtrxj/qndKlsQwtX

Initial Root Token: hvs.nWprgl3SPpwRLKPhCsJThohS
Vault initialized with 5 key shares and a key threshold of 3.
```

### 2. Unsealing Process
```bash
# Unseal with 3 keys
vault operator unseal <Unseal Key 1>
vault operator unseal <Unseal Key 2>  
vault operator unseal <Unseal Key 3>

# Verify status
vault status
```

#### Successful Status:

```text
Key             Value
---             -----
Seal Type       shamir
Initialized     true
Sealed          false
Total Shares    5
Threshold       3
Version         1.15.0
```

### 3. Authentication
```bash
# Login with root token
vault login hvs.nWprgl3SPpwRLKPhCsJThohS
```

## Secret Management
### 1. Enable KV Secrets Engine
```bash
# Enable KV v2 at secret/ path
vault secrets enable -path=secret kv-v2
```
### 2. Basic Secret Operations
```bash
# Create/Update secret
vault kv put secret/studentdb \
  POSTGRES_USER=postgres \
  POSTGRES_PASSWORD=postgres123 \
  POSTGRES_DB=studentdb

# Read secret
vault kv get secret/studentdb

# Read specific field
vault kv get -field=POSTGRES_PASSWORD secret/studentdb

# List secrets
vault kv list secret/

# Delete secret (soft delete)
vault kv delete secret/studentdb

# Undelete secret
vault kv undelete -versions=1 secret/studentdb

# Destroy secret (permanent)
vault kv destroy -versions=1 secret/studentdb
```

### 3. Policy Management
```bash
# Create policy file
cat > /tmp/studentdb-policy.hcl << EOF
path "secret/data/studentdb" {
  capabilities = ["read"]
}

path "secret/data/studentdb/*" {
  capabilities = ["read"]
}
EOF

# Apply policy
vault policy write studentdb-policy /tmp/studentdb-policy.hcl

# Create token with policy
vault token create -policy=studentdb-policy -period=24h
```

## Access Methods

### 1. Direct Pod Access
```bash
# Access Vault container
kubectl exec -n vault -it deployment/vault -- /bin/sh

# Set environment
export VAULT_ADDR='http://127.0.0.1:8200'
vault login <token>
```

### 2. Port Forwarding (Recommended)
```bash
# Terminal 1: Port forward
kubectl port-forward -n vault deployment/vault 8200:8200

# Terminal 2: Local access
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='hvs.nWprgl3SPpwRLKPhCsJThohS'
vault status
vault kv get secret/studentdb
```

### 3. API Access via curl
```bash
# With port-forward running
curl -s \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  http://localhost:8200/v1/secret/data/studentdb | jq

# Response structure:
{
  "data": {
    "data": {
      "POSTGRES_PASSWORD": "postgres123",
      "POSTGRES_USER": "postgres"
    },
    "metadata": {
      "created_time": "2025-10-15T14:13:00.60060261Z",
      "version": 1
    }
  }
}
```

### 4. Kubernetes Authentication (Advanced)
```bash
# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure with Kubernetes API info
vault write auth/kubernetes/config \
  kubernetes_host="https://$KUBERNETES_SERVICE_HOST:$KUBERNETES_SERVICE_PORT" \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create role for applications
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=default \
  bound_service_account_namespaces=default \
  policies=studentdb-policy \
  ttl=1h
```

## External Secrets Integration

### 1. Create ESO Policy
```bash
# Policy for External Secrets Operator
cat > /tmp/eso-policy.hcl << EOF
path "secret/data/studentdb" {
  capabilities = ["read"]
}
EOF

vault policy write eso-policy /tmp/eso-policy.hcl
```
### 2. Generate ESO Token
```bash
# Create orphan token with policy
vault token create -policy=eso-policy -period=24h -orphan -format=json
```

### 3. Store Token as Kubernetes Secret
```bash
# Create namespace for ESO
kubectl create ns external-secrets

# Create secret with Vault token
kubectl create secret generic vault-token \
  --from-literal=token=hvs.CAESIHGbl96lzeJ0GdqYQEWYaZ4hLNS0_fyQRhXfXr3_2GAjGh4KHGh2cy5nRVkDRTdHNFdqVWxXZUZwSEM0TXE \
  -n external-secrets
```

### 4. ExternalSecret Resource Example
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: studentdb-secret
  namespace: default
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: studentdb-credentials
  data:
  - secretKey: POSTGRES_USER
    remoteRef:
      key: secret/studentdb
      property: POSTGRES_USER
  - secretKey: POSTGRES_PASSWORD
    remoteRef:
      key: secret/studentdb
      property: POSTGRES_PASSWORD
```

## Persistence & Backup

### Data Persistence
- Storage: 512Mi PVC using standard StorageClass
- Location: /vault/data inside container
- Node Affinity: Always scheduled on minikube-m03

### Backup Procedures
```bash
# Manual backup from node
minikube ssh -n minikube-m03
sudo tar -czf /tmp/vault-backup-$(date +%Y%m%d).tar.gz /tmp/hostpath-provisioner/vault/vault-data/

# Copy backup to host
minikube cp minikube-m03:/tmp/vault-backup-20241015.tar.gz ./vault-backup.tar.gz
```

### Restart/Recovery Procedure

```bash
# After cluster restart
minikube start

# Verify Vault pod
kubectl get pods -n vault

# Unseal Vault (required after restart)
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key1>
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key2>
kubectl exec -n vault -it deployment/vault -- vault operator unseal <key3>

# Authenticate and verify
kubectl exec -n vault -it deployment/vault -- vault login <root-token>
kubectl exec -n vault -it deployment/vault -- vault kv get secret/studentdb
```

## Troubleshooting

### Common Issues & Solutions

#### 1. Vault Pod Not Starting
```bash
# Check pod status
kubectl describe pod -n vault vault-xxxxx

# Check logs
kubectl logs -n vault deployment/vault

# Check init container logs
kubectl logs -n vault vault-xxxxx -c init-permissions
```


#### 2. Permission Denied Errors
```bash
# Fix permissions on hostPath
minikube ssh -n minikube-m03
sudo chown -R 100:1000 /tmp/hostpath-provisioner/vault/vault-data/
sudo chmod 755 /tmp/hostpath-provisioner/vault/vault-data/
```

#### 3. Vault Sealed State
```bash
# Check status
vault status

# If sealed, unseal with 3 keys
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>
```

#### 4. Authentication Issues
```bash
# Always authenticate first
vault login <token>

# Check token validity
vault token lookup

# List policies
vault policy list
```

#### 5. KV Engine Not Enabled

```bash
# Enable KV v2 if not present
vault secrets enable -path=secret kv-v2

# Verify secrets engines
vault secrets list
```

### Diagnostic Commands
```bash
# Comprehensive status check
kubectl get all,pvc,configmap -n vault

# Check node assignment
kubectl get pods -n vault -o wide

# Check resource usage
kubectl top pod -n vault

# Check events
kubectl get events -n vault --sort-by=.lastTimestamp
```

## Security Considerations

### Current Security Posture

| **Aspect**             | **Status**    | **Notes**             |
| ---------------------- | ------------- | --------------------- |
| **RunAsNonRoot**       | ✅ Implemented | UID 100               |
| **Persistent Storage** | ✅ Encrypted   | Filesystem encryption |
| **Network Exposure**   | ✅ ClusterIP   | Internal only         |
| **Authentication**     | ✅ Token-based | Root + policies       |
| **Unsealing**          | ✅ Manual      | 3-of-5 threshold      |


### Production Enhancements Needed
#### 1. Enable TLS
```hcl
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_cert_file = "/vault/tls/tls.crt"
  tls_key_file = "/vault/tls/tls.key"
  tls_min_version = "tls12"
}
```

#### 2. Auto-unseal with Cloud KMS
```hcl
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "key-id"
}
```

#### 3. Audit Logging
```hcl
audit "file" {
  path = "/vault/logs/audit.log"
  log_raw = true
}
```

#### 4. Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vault-ingress
  namespace: vault
spec:
  podSelector:
    matchLabels:
      app: vault
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: external-secrets
    ports:
    - protocol: TCP
      port: 8200
```

### Key Management Best Practices

#### CRITICAL: Secure Storage Required For:
- 5 Unseal Keys (need 3 to unseal)
- Root Token
- Application-specific tokens
- Backup encryption keys

#### Recommended:
- Use secure secret management for the unseal keys
- Implement key rotation policies
- Use separate tokens for different applications
- Monitor token usage and expiration

## Maintenance Procedures

### Regular Maintenance Tasks
#### 1. Storage Monitoring
```bash
# Check storage usage
kubectl exec -n vault deployment/vault -- df -h /vault/data

# Check PVC status
kubectl get pvc -n vault
```

#### 2. Token Rotation
```bash
# Create new tokens with expiration
vault token create -policy=app-policy -period=24h -renewable=true

# Revoke old tokens
vault token revoke <token>
```
#### 3. Backup Verification
```bash
# Regular backup testing
minikube ssh -n minikube-m03 -- \
  "sudo tar -tzf /tmp/vault-backup-latest.tar.gz | head -10"

# Test restore procedure in non-production
```

#### 4. Log Monitoring
```bash
# Check for errors
kubectl logs -n vault deployment/vault --tail=50 | grep -i error

# Monitor audit logs (when enabled)
kubectl exec -n vault deployment/vault -- tail -f /vault/logs/audit.log
```

### Scaling Considerations

#### For Production Deployment:
- High Availability: Deploy 3+ Vault instances with integrated storage
- Cloud Integration: Use cloud KMS for auto-unseal
- Monitoring: Implement Prometheus metrics and alerting
- Disaster Recovery: Regular snapshots and cross-region replication
- Performance: Tune resource limits based on load

#### Resource Recommendations:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi" 
    cpu: "500m"
```

### Verification Checklist

#### Post-Installation Verification
- Vault pod running in vault namespace
- Persistent volume bound and mounted
- Vault initialized and unsealed
- KV v2 secrets engine enabled at secret/
- Sample secret created and readable
- Policies created for application access
- External Secrets token generated
- Port forwarding working correctly
- API access functional

#### Integration Testing
- Application can retrieve secrets via External Secrets
- Secrets update propagation working
- Backup/restore procedure tested
- Unsealing process documented and tested
- Security policies enforced


# External Secrets Operator with Vault - Documentation

## Overview
### Purpose
External Secrets Operator (ESO) automates the synchronization of secrets from external secret management systems (like HashiCorp Vault) into Kubernetes Secrets. This provides a secure, automated pipeline for secret management in Kubernetes.

### Key Benefits
- Centralized Secret Management: Single source of truth in Vault
- Automatic Synchronization: Secrets automatically sync to Kubernetes
- Security: No hardcoded credentials in Kubernetes manifests
- Audit Trail: All secret access tracked through Vault
- Dynamic Updates: Secrets update automatically when changed in Vault

### Architecture
#### Component Diagram
```text
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Kubernetes    │    │   External       │    │   HashiCorp Vault  │
│   Applications  │◄───│   Secrets        │◄───│   (Vault Server)   │
│                 │    │   Operator       │    │                    │
└─────────────────┘    └──────────────────┘    └────────────────────┘
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                          ┌──────────────┐
                          │ Kubernetes   │
                          │   Secrets    │
                          └──────────────┘
```

#### Data Flow
- Vault Stores Secrets → Secrets stored in KV v2 engine
- ESO Watches Vault → Operator periodically checks for changes
- Kubernetes Secrets Created → ESO creates/updates K8s secrets
- Applications Consume → Pods mount secrets as volumes or env vars

### Namespace Strategy
| **Namespace**        | **Purpose**       | **Components**                          |
| -------------------- | ----------------- | --------------------------------------- |
| **external-secrets** | ESO Operations    | ESO Deployment, Service Account         |
| **vault**            | Secret Management | Vault Server, Persistent Storage        |
| **student-api**      | Application       | API Pods, Database, Application Secrets |
| **observability**    | Monitoring        | Grafana, Prometheus, Exporter Secrets   |

## Prerequisites
### System Requirements

- Kubernetes cluster (Minikube 3-node cluster)
- Vault installed and running in vault namespace
- Vault initialized and unsealed
- kubectl configured and accessible
- Proper node labeling:
  - minikube-m03: type=dependent_services (Vault, ESO)

### Pre-deployment Verification
```bash
# Verify cluster nodes and labels
kubectl get nodes --show-labels

# Verify Vault is running
kubectl get pods -n vault

# Verify Vault is accessible
kubectl exec -n vault -it deployment/vault -- vault status

# Check Vault secrets exist
kubectl exec -n vault -it deployment/vault -- \
  vault kv get secret/studentdb
```

### Installation Steps

#### Step 1: Install External Secrets Operator CRDs
```bash
# Install official ESO CRDs and controller
kubectl apply -f https://github.com/external-secrets/external-secrets/releases/download/v0.9.9/external-secrets.yaml

# Verify CRDs are installed
kubectl get crd | grep external-secrets.io
```

#### Step 2: Deploy ESO Configuration
```bash
# Set Vault token as environment variable
export VAULT_TOKEN="hvs.nWprgl3SPpwRLKPhCsJThohS"

# Deploy using envsubst for variable substitution
envsubst < external-secrets.yaml | kubectl apply -f -
```

#### Step 3: Verify Deployment
```bash
# Check ESO operator is running
kubectl get pods -n external-secrets

# Check ClusterSecretStore status
kubectl get clustersecretstores

# Check ExternalSecret resources
kubectl get externalsecrets -A
```

## ESO Resources - Quick Reference
### 1. Namespaces
- Purpose: Logical separation of components and secret domains
- external-secrets: Dedicated namespace for ESO operator and management components
- student-api: Houses application workloads and database-related secrets
- observability: Contains monitoring stack tools and their configuration secrets

### 2. ServiceAccount
- Purpose: Provides identity for ESO to interact with Kubernetes API
- ServiceAccount used by ESO pods for authentication and API operations
- Serves as the identity that RBAC rules are applied to for authorization

### 3. ClusterRole
- Purpose: Defines the permissions ESO needs across the entire cluster
- Grants full access to manage secrets, external secrets, and secret stores
- Provides read access for namespace discovery and service connectivity

### 4. ClusterRoleBinding
- Purpose: Connects the ServiceAccount to the ClusterRole permissions
- Links the ESO ServiceAccount to the defined ClusterRole rules
- Enables cluster-wide access for managing secrets across all namespaces

### 5. Vault Token Secret
- Purpose: Securely stores authentication token for Vault access
- Kubernetes Secret containing the Vault token for API authentication
- ESO reads this token to establish secure connection with Vault server

### 6. ESO Deployment
- Purpose: Runs the External Secrets Operator controller
- Deployment that runs the ESO container which manages secret synchronization
- Uses the designated ServiceAccount and operates in its dedicated namespace

### 7. ClusterSecretStore
- Purpose: Configures the connection to external secret manager (Vault)
- Defines Vault server endpoint, secrets path, and authentication method
- Cluster-scoped resource that can be referenced from any namespace

### 8. ExternalSecrets (3 instances)
- Purpose: Declares what secrets to sync and their destination
#### studentdb-secrets → student-api namespace
- Synchronizes PostgreSQL database credentials from Vault to application namespace
- Creates Kubernetes secret with database username and password for app consumption
#### postgres-exporter-secret → observability namespace
- Fetches monitoring credentials for PostgreSQL exporter from Vault
- Provides database connection details and credentials for metrics collection
#### grafana-secret → observability namespace
- Retrieves Grafana administration credentials from Vault secrets
- Supplies admin username and password for Grafana dashboard access

## Troubleshooting
### Diagnostic Commands
#### 1. Verify ESO Operator Status
```bash
# Check ESO pod is running
kubectl get pods -n external-secrets

# Check ESO logs for errors
kubectl logs -n external-secrets deployment/external-secrets-operator

# Verify ESO can access Kubernetes API
kubectl auth can-i get secrets --as=system:serviceaccount:external-secrets:external-secrets
```

#### 2. Verify ClusterSecretStore Connectivity
```bash
# Check ClusterSecretStore status
kubectl get clustersecretstores
kubectl describe clustersecretstore vault-backend

# Expected output:
# Status:
#   Conditions:
#     Last Transition Time:  2025-09-17T08:32:40Z
#     Message:               store validated
#     Reason:                Valid
#     Status:                True
#     Type:                  Ready
```

#### 3. Verify ExternalSecret Synchronization
```bash
# Check ExternalSecret status across all namespaces
kubectl get externalsecrets -A

# Check specific ExternalSecret details
kubectl describe externalsecret studentdb-secrets -n student-api
kubectl describe externalsecret postgres-exporter-secret -n observability

# Check sync status in status conditions
kubectl get externalsecret studentdb-secrets -n student-api -o jsonpath='{.status.conditions}'
```

#### 4. Verify Kubernetes Secrets Creation
```bash
# Check secrets are created in target namespaces
kubectl get secrets -n student-api
kubectl get secrets -n observability

# Verify secret contents
kubectl get secret postgres-secret -n student-api -o jsonpath='{.data.POSTGRES_USER}' | base64 -d
kubectl get secret postgres-secret -n student-api -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d
```

#### 5. Verify Vault Connectivity
```bash
# Test Vault connectivity from within cluster
kubectl run vault-test --image=curlimages/curl -it --rm -- \
  curl -s http://vault-service.vault.svc.cluster.local:8200/v1/sys/health

# Verify Vault secrets are accessible
kubectl exec -n vault -it deployment/vault -- \
  vault kv get secret/studentdb
```

## Common Issues and Solutions

### Issue 1: ExternalSecret in "SecretSyncedError" State
**Symptoms:**
- ExternalSecret status shows Ready: False
- Error message about missing secrets or permissions

**Diagnosis:**
```bash
kubectl describe externalsecret <name> -n <namespace>
```

**Common Causes & Solutions:**

#### 1. Missing Vault Secret:

```bash
# Verify secret exists in Vault
kubectl exec -n vault -it deployment/vault -- vault kv get secret/studentdb
```

#### 2. Incorrect Vault Path:

- Ensure path matches KV v2 structure (secret/data/studentdb)
- Check key property in ExternalSecret matches Vault path

#### 3. Token Permissions:

```bash
# Verify token has read permissions
kubectl exec -n vault -it deployment/vault -- \
  vault token capabilities secret/data/studentdb
```

### Issue 2: Vault Connectivity Problems
**Symptoms:**
- ClusterSecretStore status not Ready
- Network connection errors in ESO logs

**Solutions:**
```bash
# Verify Vault service exists
kubectl get svc -n vault

# Test DNS resolution
kubectl run dns-test --image=busybox -it --rm -- nslookup vault-service.vault.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n vault
```

### Issue 3: RBAC Permission Errors
**Symptoms:**
- ESO logs show "forbidden" errors
- ExternalSecrets not processed

**Solutions:**
```bash
# Verify ServiceAccount permissions
kubectl auth can-i get secrets --as=system:serviceaccount:external-secrets:external-secrets

# Check ClusterRole binding
kubectl describe clusterrolebinding external-secrets-cluster-role-binding
```

## Maintenance & Operations

### Regular Monitoring
#### 1. Health Checks
```bash
# Daily health check script
#!/bin/bash
echo "=== ESO Status ==="
kubectl get pods -n external-secrets

echo "=== ClusterSecretStore Status ==="
kubectl get clustersecretstores

echo "=== ExternalSecret Status ==="
kubectl get externalsecrets -A

echo "=== Secret Sync Status ==="
for ns in student-api observability; do
  echo "--- $ns ---"
  kubectl get secrets -n $ns
done
```

#### 2. Log Monitoring
```bash
# Tail ESO logs for real-time monitoring
kubectl logs -n external-secrets deployment/external-secrets-operator -f

# Check for specific error patterns
kubectl logs -n external-secrets deployment/external-secrets-operator | grep -i error
```

### Secret Rotation Procedures
#### 1. Rotate Vault Secrets
```bash
# Update secret in Vault
kubectl exec -n vault -it deployment/vault -- \
  vault kv put secret/studentdb \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=new_secure_password_123

# The Kubernetes secret will auto-update within refreshInterval (1h)
# Or force immediate update by deleting and recreating ExternalSecret
kubectl delete externalsecret studentdb-secrets -n student-api
kubectl apply -f external-secrets.yaml
```

#### 2. Rotate Vault Token
```bash
# Generate new token in Vault
kubectl exec -n vault -it deployment/vault -- \
  vault token create -policy=default -period=24h

# Update Kubernetes secret
kubectl create secret generic vault-token \
  --from-literal=token=new_token_value \
  -n external-secrets --dry-run=client -o yaml | kubectl apply -f -
```

#### Backup and Recovery

#### 1. Backup ESO Configuration
```bash
# Backup all ESO-related resources
kubectl get externalsecrets -A -o yaml > externalsecrets-backup-$(date +%Y%m%d).yaml
kubectl get clustersecretstores -o yaml > clustersecretstores-backup-$(date +%Y%m%d).yaml
kubectl get -n external-secrets secret vault-token -o yaml > vault-token-backup-$(date +%Y%m%d).yaml
```

#### 2. Disaster Recovery
```bash
# Restore ESO configuration
kubectl apply -f externalsecrets-backup-$(date +%Y%m%d).yaml
kubectl apply -f clustersecretstores-backup-$(date +%Y%m%d).yaml
kubectl apply -f vault-token-backup-$(date +%Y%m%d).yaml

# Verify synchronization
kubectl get externalsecrets -A
kubectl get secrets -n student-api
```

### Security Considerations

| **Aspect**              | **Status**   | **Implementation**                     |
| ----------------------- | ------------ | -------------------------------------- |
| **Namespace Isolation** |  Implemented | Separate namespaces for components     |
| **Service Account**     |  Implemented | Dedicated SA with minimal permissions  |
| **Token Security**      |  Implemented | Stored as Kubernetes Secret            |
| **Network Security**    |  Basic       | ClusterIP services, no TLS             |
| **Access Control**      |  Implemented | RBAC with principle of least privilege |

### Security Best Practices

#### 1. Vault Token Management
```bash
# Create dedicated policy for ESO
kubectl exec -n vault -it deployment/vault -- \
  vault policy write eso-policy - <<EOF
# Read-only access to specific paths
path "secret/data/studentdb" {
  capabilities = ["read"]
}

path "monitoring/data/*" {
  capabilities = ["read"]
}

# List access for discovery
path "secret/metadata/*" {
  capabilities = ["list"]
}

path "monitoring/metadata/*" {
  capabilities = ["list"]
}
EOF

# Create token with limited TTL
kubectl exec -n vault -it deployment/vault -- \
  vault token create -policy=eso-policy -period=24h -renewable=true
```

#### 2. Network Security Enhancements
```yaml
# Network Policy for ESO (optional)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-eso-vault
  namespace: external-secrets
spec:
  podSelector:
    matchLabels:
      app: external-secrets
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: vault
    ports:
    - protocol: TCP
      port: 8200
```

#### 3. Production Security Checklist

- Enable TLS for Vault communication
- Use Vault namespaces for multi-tenancy
- Implement automatic token rotation
- Enable Vault audit logging
- Use Kubernetes service accounts for Vault auth instead of tokens
- Implement network policies to restrict traffic
- Regular security scanning of container images

# Student API Helm Deployment - Documentation

### Overview
A Helm-managed Flask REST API deployment with PostgreSQL database integration, featuring database migrations and secret management.

### Architecture Components
#### 1. Namespace
- Name: student-api
- Managed By: Helm
- Labels: Standard Helm labels for resource tracking
- Purpose: Isolates all application resources

#### 2. Configuration Management
- ConfigMap: flask-config
- Stores non-sensitive configuration:
  - POSTGRES_HOST: "postgres" (Kubernetes service name)
  - POSTGRES_PORT: "5432" (Database port)
  - POSTGRES_DB: "studentdb" (Database name)
- Secret: postgres-secret
- Stores sensitive credentials (referenced from ExternalSecret):
  - POSTGRES_USER: Database username
  - POSTGRES_PASSWORD: Database password

#### 3. Application Deployment
- Deployment: flask-api
  - Replicas: 2 (high availability)
  - Node Selection: Runs on nodes with label type: application
  - Image: akhilthyadi/flask-app:7.0.0
- Pod Structure:
  - Init Container: db-migrations
  - Purpose: Database schema initialization and migrations
  - Working Directory: /api/app
- Environment:
  - Mix of ConfigMap (non-sensitive) and Secret (sensitive) values
- Process:
  - Waits for PostgreSQL readiness using pg_isready
  - Executes database migrations with flask db upgrade
- Main Container: flask-api
  - Port: 5000 (Flask application port)
  - Environment: Same configuration as init container
  - Readiness: Inherits from successful init container completion

#### 4. Network Exposure
- Service: flask-api-service
- Type: NodePort (external access)
  - Port Mapping:
  - Service Port: 80
- Target Port: 5000 (container port)
- Selector: app: flask-api (matches deployment pods)

### Key Features
#### 1. Database Integration
- Pre-startup migrations: Ensures database schema is current before app starts
- Connection resilience: Init container waits for database availability
- Secret separation: Credentials stored securely, separate from configuration

#### 2. Helm Management
- Standard labels: app.kubernetes.io/* labels for consistent resource management
- Release tracking: Annotations track Helm release information
- Component identification: Clear component labeling (api, config, service)

#### 3. Security & Configuration
- ConfigMap: Non-sensitive configuration
- Secret references: Sensitive data from ExternalSecret/Vault
- Node isolation: Specific node selection for deployment control

### Dependencies
#### 1. Required Infrastructure
- Kubernetes Cluster: With proper node labeling
- PostgreSQL Database: Service named postgres in accessible namespace
- External Secrets Operator: For secret management from Vault
- Node Preparation:
  - Application nodes: type: application
  - Database nodes: Appropriate labeling for PostgreSQL

#### 2. External Services
- Vault: For secret storage and management
- ExternalSecret: postgres-secret must be populated before deployment

### Deployment Sequence
- Namespace Creation → Isolate application resources
- ConfigMap Application → Apply non-sensitive configuration
- Secret Verification → Ensure postgres-secret exists via ExternalSecret
- Deployment Creation →
  - Init container runs migrations
  - Main containers start after successful migrations
  - Service Exposure → Make API available via NodePort

# PostgresDB Manifest - Documentation

### Overview
A Helm-managed PostgreSQL database deployment for the Student API application, featuring persistent storage, secure credential management, and proper Kubernetes service exposure.

### Architecture Components
#### 1. Namespace
- Name: student-api (shared with application)
- Managed By: Helm
- Labels: Standard Helm labels with chart version tracking
- Purpose: Shared namespace for both application and database components

### 2. Configuration Management
- ConfigMap: postgres-config
- Stores database connection configuration:
  - POSTGRES_HOST: "postgres" (Kubernetes service name)
  - POSTGRES_PORT: "5432" (Database port)
  - POSTGRES_DB: "studentdb" (Database name)

**Key Features:**
- Version tracking: app.kubernetes.io/version: "15"
- Component identification: app.kubernetes.io/component: database-config

### 3. Storage Management
- PersistentVolumeClaim: postgres-pvc
- Access Mode: ReadWriteOnce (single node access)
  - Storage Request: 1Gi
  - Purpose: Persistent storage for database data
  - Component Label: app.kubernetes.io/component: database-storage

### 4. Database Deployment
- Deployment: postgres
- Replicas: 1 (single instance for database)
- Node Selection: Runs on nodes with label type: database
- Image: postgres:15 (specific version for stability)
- Port: 5432 (standard PostgreSQL port)

**Container Configuration:**
- Environment Variables:
  - From Secrets (sensitive):
  - POSTGRES_USER: Database superuser
  - POSTGRES_PASSWORD: Database password

- From ConfigMap (non-sensitive):
  - POSTGRES_DB: Database name
  - POSTGRES_HOST: Service hostname
  - POSTGRES_PORT: Service port

**Volume Mounts:**
- Mount Path: /var/lib/postgresql/data
- Volume: postgres-storage (backed by PVC)
- Purpose: Persistent data storage across pod restarts

5. Network Exposure
- Service: postgres
- Type: ClusterIP (internal cluster access only)
- Port: 5432 (matches container port)
- Selector: app: postgres (matches deployment pods)
- Purpose: Provides stable DNS name for database access within cluster

### Key Features
### 1. Storage Persistence
- PVC-backed: Data survives pod restarts and rescheduling
- Proper mount: PostgreSQL data directory mounted to persistent storage
- Size management: 1GB initial allocation, scalable as needed

### 2. Security & Configuration
- Secret separation: Credentials managed separately via ExternalSecret/Vault
- ConfigMap isolation: Non-sensitive configuration in ConfigMap
- Internal service: ClusterIP type limits exposure to cluster internal only

### 3. Helm Management
- Version tracking: Clear PostgreSQL version identification
- Component labeling: Detailed component breakdown (database, config, service, storage)
- Release annotations: Helm release tracking for management

### 4. Node Management
- Dedicated nodes: Database runs on type: database labeled nodes
- Isolation: Separates database from application workloads
- Resource control: Enables specialized node configuration for database performance

### Dependencies
1. Required Infrastructure
- Kubernetes Cluster: With proper node labeling
- Storage Class: Supports dynamic provisioning for PVC
- External Secrets Operator: For secret management from Vault
- Node Preparation:
  - Database nodes: type: database label
  - Storage: Support for ReadWriteOnce volumes

### 2. External Services
- Vault: For secret storage of database credentials
- ExternalSecret: postgres-secret must be populated before deployment

### Deployment Sequence
1. Namespace Verification → Ensure shared namespace exists
2. ConfigMap Application → Apply database configuration
3. PVC Creation → Set up persistent storage
4. Secret Verification → Ensure postgres-secret exists via ExternalSecret
5. Deployment Creation → Start PostgreSQL database with persistent storage
6. Service Exposure → Create ClusterIP service for internal access

### Database Configuration Details
#### Environment Variables Usage:
- POSTGRES_USER/POSTGRES_PASSWORD: Authentication (from Secret)
- POSTGRES_DB: Default database creation (from ConfigMap)
- POSTGRES_HOST/POSTGRES_PORT: Service configuration (from ConfigMap)

#### Storage Configuration:
- Data Persistence: All database files stored in mounted PVC
- Data Survival: Database state maintained across pod restarts
- Backup Ready: Persistent storage enables backup strategies

# Vault & External Secrets Troubleshooting Guide
### Overview
This guide covers troubleshooting Vault deployment on Kubernetes and integration with External Secrets Operator (ESO) for secret synchronization.

### Quick Start Troubleshooting Flow
```bash
# 1. Check Vault status
kubectl get all -n vault

# 2. Check ESO status
kubectl get all -n external-secrets

# 3. Verify ExternalSecret status
kubectl get externalsecrets -n student-api

# 4. Check created secrets
kubectl get secrets -n student-api
```

### Vault-Specific Issues

#### Issue 1: Vault Pod Pending
**Symptoms:**
- Vault pod stuck in Pending status
- No containers starting

**Diagnosis:**
```bash
# Check pod events
kubectl describe pod <vault-pod> -n vault

# Check node labels
kubectl get nodes --show-labels
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.type
```

**Solutions:**
- Add missing node label:
```bash
kubectl label node <node-name> type=dependent_services --overwrite
```
- Update deployment nodeSelector:
```yaml
nodeSelector:
  type: dependent_services
```

### Issue 2: Vault Pod CrashLoopBackOff

**Symptoms:**
- Vault pod starts and immediately crashes
- CrashLoopBackOff status

**Diagnosis:**
```bash
# Check Vault logs
kubectl logs <vault-pod> -n vault

# Check pod description
kubectl describe pod <vault-pod> -n vault
```

### Common Errors & Fixes:

| **Error Message**                                                   | **Cause**                                      | **Solution**                                            |
| ------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------- |
| **A storage backend must be specified**                             | Missing storage backend in non-dev mode        | Add `-dev` flag or configure a storage backend          |
| **You cannot specify a custom root token ID outside of "dev" mode** | Using `VAULT_DEV_ROOT_TOKEN_ID` without `-dev` | Remove token ID or start Vault with the `-dev` flag     |
| **Couldn't start vault with IPC_LOCK**                              | `IPC_LOCK` capability issue                    | Grant `IPC_LOCK` capability or set `disable_mlock=true` |

- Fix Deployment for Dev Mode:
```yaml
args:
  - "server"
  - "-dev"
  - "-dev-root-token-id=root"
```

### Issue 3: Vault CLI HTTPS/HTTP Mismatch

**Symptoms:**

```txt
Error: http: server gave HTTP response to HTTPS client
Cause: Vault dev server runs on HTTP, CLI defaults to HTTPS
```

**Solution:**
```bash
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'
vault status
```

### Issue 4: Cannot Exec into Vault Pod
**Symptoms:**
```bash
kubectl exec -it deploy/vault -n vault -- /bin/sh
error: Internal error occurred: unable to upgrade connection: container not found ("vault")
```

**Solutions:**
- Use pod name instead of deployment:
```bash
kubectl get pods -n vault
kubectl exec -it <pod-name> -n vault -- /bin/sh
```
- If pod is crashing, check logs instead:
```bash
kubectl logs <pod-name> -n vault
```

### Issue 5: Vault Secrets Not Persisting
**Symptoms:**
- Secrets disappear after pod restart
- Changes not saved
- Cause: Dev mode uses in-memory storage

**Solutions:**
- For development - recreate secrets after restart
- For production - use persistent storage:
```yaml
storage "file" {
  path = "/vault/data"
}
```

## External Secrets Operator (ESO) Issues

### Issue 1: ESO Not Creating Secrets

**Symptoms:**
- ExternalSecret created but no Kubernetes secret generated
- kubectl get secrets shows no expected secrets

**Diagnosis:**
```bash
# Check ExternalSecret status
kubectl get externalsecrets -n student-api
kubectl describe externalsecret student-api-secrets -n student-api

# Check ESO logs
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets
```

### Common Errors:

| **Error**                                                                                        | **Cause**                | **Solution**                                                 |
| ------------------------------------------------------------------------------------------------ | ------------------------ | ------------------------------------------------------------ |
| **failed to get API group resources: v1beta1: the server could not find the requested resource** | ESO version mismatch     | Upgrade to version **v0.19.2+**                              |
| **secrets is forbidden: User cannot list resource "secrets"**                                    | Insufficient permissions | Add proper **ClusterRole** and bind it to the ServiceAccount |

### Issue 2: ESO Permission Issues
**Symptoms:**
- ESO logs show permission denied errors
- secrets is forbidden messages

**Diagnosis:**
```bash
# Check ServiceAccount permissions
kubectl auth can-i list secrets --as=system:serviceaccount:external-secrets:external-secrets-sa

# Check ESO logs
kubectl logs -n external-secrets deployment/external-secrets
```

**Solution - Create Proper RBAC:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: external-secrets
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: external-secrets-role
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["external-secrets.io"]
  resources: ["externalsecrets", "clustersecretstores"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: external-secrets-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: external-secrets-role
subjects:
- kind: ServiceAccount
  name: external-secrets-sa
  namespace: external-secrets
```

### Issue 3: ESO Version Mismatch

**Symptoms:**
- API version conflicts
- CRD compatibility issues

**Solution - Upgrade via Helm:**
```bash
# Uninstall old version
helm uninstall external-secrets -n external-secrets

# Install latest version
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace \
  --version 0.19.2
```

### Issue 4: Vault Backend Connection Issues
**Symptoms:**
- ExternalSecret status shows SecretSynced: False
- Connection errors in ESO logs

**Diagnosis:**
```bash
# Check ClusterSecretStore
kubectl get clustersecretstores
kubectl describe clustersecretstore vault-backend

# Verify Vault connectivity
kubectl exec -it <vault-pod> -n vault -- vault status
```

**Solution - Verify ClusterSecretStore Configuration:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"
      path: "secret"
      version: "v2"
      auth:
        # Use Kubernetes authentication
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

## Step-by-Step Troubleshooting Procedures

#### Phase 1: Vault Health Check
```bash
# 1. Check Vault deployment
kubectl get deployment vault -n vault
kubectl describe deployment vault -n vault

# 2. Check Vault pods
kubectl get pods -n vault -l app=vault
kubectl describe pod <vault-pod> -n vault

# 3. Check Vault logs
kubectl logs -n vault -l app=vault

# 4. Verify Vault service
kubectl get svc -n vault
kubectl describe svc vault -n vault

# 5. Test Vault connectivity
kubectl port-forward svc/vault -n vault 8200:8200 &
curl http://localhost:8200/v1/sys/health
```

### Phase 2: ESO Health Check
```bash
# 1. Check ESO deployment
kubectl get deployment -n external-secrets
kubectl describe deployment external-secrets -n external-secrets

# 2. Check ESO pods
kubectl get pods -n external-secrets -l app.kubernetes.io/name=external-secrets

# 3. Check ESO logs
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets

# 4. Verify CRDs
kubectl get crd | grep external-secrets

# 5. Check ClusterSecretStore
kubectl get clustersecretstores
kubectl describe clustersecretstore vault-backend
```

### Phase 3: ExternalSecret Verification
```bash
# 1. Check ExternalSecret status
kubectl get externalsecrets -A
kubectl describe externalsecret student-api-secrets -n student-api

# 2. Check created secrets
kubectl get secrets -n student-api
kubectl describe secret student-api-secret -n student-api

# 3. Verify secret content
kubectl get secret student-api-secret -n student-api -o jsonpath='{.data}' | base64 --decode

# 4. Check events
kubectl get events -n student-api --sort-by='.lastTimestamp'
kubectl get events -n external-secrets --sort-by='.lastTimestamp'
```

## Quick Fix Commands
### Restart Components
```bash
# Restart Vault
kubectl rollout restart deployment/vault -n vault

# Restart ESO
kubectl rollout restart deployment/external-secrets -n external-secrets

# Delete problematic pods
kubectl delete pod -n vault <vault-pod>
kubectl delete pod -n external-secrets <eso-pod>
```

### Debug Vault
```bash
# Port forward for local access
kubectl port-forward svc/vault -n vault 8200:8200 &

# Set environment variables
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

# Test Vault
vault status
vault secrets list
Debug ESO
bash
# Check ESO pod status
kubectl get pods -n external-secrets -l app.kubernetes.io/name=external-secrets

# Stream ESO logs
kubectl logs -n external-secrets -l app.kubernetes.io/name=external-secrets -f

# Check ExternalSecret events
kubectl describe externalsecret -n student-api student-api-secrets
```

### Force Secret Refresh
```bash
# Annotate ExternalSecret to force refresh
kubectl annotate externalsecret student-api-secrets -n student-api external-secrets.io/refresh-timestamp="$(date +%s)" --overwrite

# Or delete and recreate
kubectl delete externalsecret student-api-secrets -n student-api
kubectl apply -f external-secrets.yaml
```

| **Error**                                           | **Component**  | **Solution**                                          |
| --------------------------------------------------- | -------------- | ----------------------------------------------------- |
| **Pod Pending**                                     | Vault          | Check `nodeSelector` and node labels                  |
| **CrashLoopBackOff**                                | Vault          | Add `-dev` flag for development mode                  |
| **http: server gave HTTP response to HTTPS client** | Vault CLI      | Set `VAULT_ADDR=http://...`                           |
| **failed to get API group resources: v1beta1**      | ESO            | Upgrade ESO to **v0.19.2+**                           |
| **secrets is forbidden**                            | ESO            | Add proper **ClusterRole** and **ClusterRoleBinding** |
| **SecretSynced: False**                             | ExternalSecret | Check **ClusterSecretStore** configuration            |

---

# Student API Troubleshooting Guide

### Overview
This guide provides step-by-step troubleshooting for the Student Management API deployment on Kubernetes, focusing on common issues with database connectivity, environment configuration, and application startup.

## Quick Start Troubleshooting Flow
```bash
# 1. Basic health check
kubectl get all -n student-api

# 2. Pod status check
kubectl get pods -n student-api -o wide

# 3. Check init container logs
kubectl logs <pod-name> -n student-api -c db-migrations

# 4. Check main app logs
kubectl logs <pod-name> -n student-api -c flask-api

# 5. Test service connectivity
kubectl port-forward svc/flask-api-service -n student-api 5000:80
curl http://localhost:5000/health
```

## Common Issues & Solutions

### Issue 1: Database Connection Failures
**Symptoms:**
- Pods stuck in Init:Error or Init:0/1
- Logs show: could not translate host name "postgres" to address

**Diagnosis:**
```bash
# Check DNS resolution
kubectl exec -n student-api -it <pod> -c db-migrations -- nslookup postgres

# Verify service endpoints
kubectl get endpoints -n student-api postgres

# Check environment variables
kubectl exec -n student-api -it <pod> -c db-migrations -- printenv | grep POSTGRES
```

**Solutions:**

**1. Create postgres service alias:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: student-api
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
```
**2. Update environment variables:**

```bash
kubectl set env deployment/flask-api POSTGRES_HOST=postgres POSTGRES_PORT=5432 -n student-api
```

### Issue 2: Database Authentication Failures
**Symptoms:**
- Logs show: password authentication failed for user
- Init containers failing with authentication errors

**Diagnosis:**
```bash
# Check ExternalSecret status
kubectl get externalsecret -n student-api
kubectl describe externalsecret postgres-secret -n student-api

# Verify secret content
kubectl get secret postgres-secret -n student-api -o yaml
kubectl get secret postgres-secret -n student-api -o jsonpath='{.data.POSTGRES_USER}' | base64 --decode
```

**Solutions:**

**Test database connection manually:**
```bash
kubectl exec -n student-api -it <pod> -- bash -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt"'
```

**Check ExternalSecret controller logs:**
```bash
kubectl -n external-secrets logs -l app.kubernetes.io/name=external-secrets
```

### Issue 3: Malformed Database URI
**Symptoms:**
- Logs show: ValueError: invalid literal for int() with base 10: 'tcp:'
- Application fails to start with database configuration errors

**Diagnosis:**
```bash
# Check environment variables for tcp: prefix
kubectl exec -n student-api -it <pod> -c flask-api -- printenv | grep POSTGRES
```

**Solutions:**
- Remove tcp: prefix from environment variables:
```bash
kubectl set env deployment/flask-api POSTGRES_HOST=postgres POSTGRES_PORT=5432 -n student-api
```

- Verify expected environment format:
```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=student_db
```

### Issue 4: Application Import/Startup Errors
**Symptoms:**
- Logs show: Error: Could not import 'wsgi' or No such command 'db'
- Main container in CrashLoopBackOff

**Diagnosis:**
```bash
# Check application logs
kubectl logs <pod> -n student-api -c flask-api --previous

# Verify environment variables
kubectl exec -n student-api -it <pod> -c flask-api -- printenv
```

**Solutions:**
- Check FLASK_APP environment variable:
```bash
kubectl set env deployment/flask-api FLASK_APP=wsgi:app -n student-api
```
- Verify working directory and entrypoint in container configuration

### Issue 5: Image Pull and Resource Issues

**Symptoms:**
- Pods in ImagePullBackOff or ErrImagePull
- Pods in CrashLoopBackOff with OOMKilled events

**Diagnosis:**
```bash
# Check pod events
kubectl describe pod <pod-name> -n student-api

# Check resource usage
kubectl top pods -n student-api
```
**Solutions:**
- Image pull issues:
  - Verify image name and tag
  - Check registry authentication with imagePullSecrets

**Memory issues:**

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Step-by-Step Troubleshooting Procedure
### Phase 1: Basic Cluster Health
```bash
# 1. Verify namespace and resources
kubectl get ns
kubectl get all -n student-api

# 2. Check pod status
kubectl get pods -n student-api -o wide --show-labels

# 3. View recent events
kubectl get events -n student-api --sort-by='.lastTimestamp'
```

### Phase 2: Init Container Investigation
```bash
# 1. Check init container logs
kubectl logs <pod> -n student-api -c db-migrations

# 2. If restarted, check previous logs
kubectl logs <pod> -n student-api -c db-migrations --previous

# 3. Verify init container environment
kubectl exec -n student-api -it <pod> -c db-migrations -- printenv
```

### Phase 3: Main Application Investigation
```bash
# 1. Check main application logs
kubectl logs <pod> -n student-api -c flask-api

# 2. Verify application environment
kubectl exec -n student-api -it <pod> -c flask-api -- printenv | grep -i POSTGRES

# 3. Test database connectivity from application pod
kubectl exec -n student-api -it <pod> -c flask-api -- bash -c 'echo "Testing DB connection..." && PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"'
```

### Phase 4: Service and Networking
```bash
# 1. Verify services
kubectl get svc -n student-api
kubectl describe svc flask-api-service -n student-api

# 2. Check endpoints
kubectl get endpoints -n student-api

# 3. Test application health
kubectl port-forward svc/flask-api-service -n student-api 5000:80 &
curl -v http://localhost:5000/health
```

## Quick Fix Commands
### Environment Variable Updates
```bash
# Quick environment patch
kubectl set env deployment/flask-api \
  POSTGRES_HOST=postgres \
  POSTGRES_PORT=5432 \
  FLASK_APP=wsgi:app \
  -n student-api
```

### Restart Deployment
```bash
# Restart with new configuration
kubectl rollout restart deployment/flask-api -n student-api

# Monitor rollout status
kubectl rollout status deployment/flask-api -n student-api

```

### Secret Verification
```bash
# Check all secrets in namespace
kubectl get secrets -n student-api

# Decode specific secret values
kubectl get secret postgres-secret -n student-api -o jsonpath='{.data.POSTGRES_USER}' | base64 --decode
kubectl get secret postgres-secret -n student-api -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 --decode
```

### Debug Pod Creation
```bash
# Create debug pod for testing
kubectl run -it debug-pod --image=bitnami/kubectl --restart=Never -n student-api -- bash

# Test DNS resolution from debug pod
nslookup postgres.student-api.svc.cluster.local

# Test database connectivity
PGPASSWORD=your_password psql -h postgres -U your_user -d your_db -c "\dt"
```

### Common Error Messages Reference
| **Error Message**                                              | **Likely Cause**                         | **Solution**                                          |
| -------------------------------------------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| **could not translate host name "postgres"**                   | DNS/service name mismatch                | Create `postgres` service or update `POSTGRES_HOST`   |
| **password authentication failed**                             | Wrong credentials in secret              | Verify `ExternalSecret` and secret content            |
| **ValueError: invalid literal for int() with base 10: 'tcp:'** | Malformed `POSTGRES_HOST`/`PORT`         | Remove `tcp:` prefix from environment variables       |
| **Error: Could not import 'wsgi'**                             | Wrong `FLASK_APP` or working directory   | Set `FLASK_APP=wsgi:app` and verify working directory |
| **ImagePullBackOff**                                           | Bad image tag or registry authentication | Check image name and `imagePullSecrets`               |
| **CrashLoopBackOff with OOMKilled**                            | Out of memory                            | Increase memory limits in deployment                  |



