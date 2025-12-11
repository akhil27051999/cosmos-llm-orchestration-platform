# Deploy REST API & its dependent services on bare metal documentation

https://github.com/user-attachments/assets/68f69596-99fe-4a12-b172-3a2725c13b37

## 1. Bootstrap Provisioning Script (provision.sh)

### Purpose & Role:
- System initialization and dependency installation script
- Automated environment setup for the Vagrant VM
- Installs all required tools for containerized deployment


### Execution Flow:

#### 1. System Preparation
- Updates package repositories and upgrades existing packages
- Sets strict error handling (exit on errors, treat unset vars as errors)

#### 2. Tool Installation Sequence
- Basic development tools (curl, git, make, python3)
- PostgreSQL client for database operations
- Docker CE with official repositories
- Kubernetes tools (kubectl, minikube) for orchestration

#### 3. Post-Installation Configuration
- Enables Docker service to start on boot
- Adds vagrant user to docker group for non-sudo access
- Provides usage instructions for the deployed environment

#### Key Dependencies:
- Requires Ubuntu-based system
- Internet connectivity for package downloads
- sudo privileges for system modifications

#### Configuration Impact:
- Docker installed with compose plugin (not standalone docker-compose)
- Kubernetes tools pre-configured for local cluster development
- System ready for both Docker Compose and Kubernetes deployments

## 2. Vagrant AWS Configuration (Vagrantfile)

### Purpose & Role:
- Infrastructure as Code definition for AWS EC2 instance
- Automates cloud environment provisioning using vagrant-aws plugin

#### 1. Infrastructure Components:
- Compute Resources
- Instance Type: t3.small (cost-effective, burstable CPU)
- AMI: Ubuntu Server (ami-054d6a336762e438e)
- Region: us-east-1 (US East N. Virginia)

#### 2. Network Configuration
- Subnet: subnet-0a03e0dbddc93b6aa (specific VPC subnet)
- Security Group: sg-09d4c5f5679711dd2 (firewall rules)
- Public IP: Enabled for external access

#### 3. Access & Security
- SSH Key: api-server.pem for secure authentication
- Username: ubuntu (standard Ubuntu user)
- Termination Protection: Enabled (prevents accidental deletion)

### Execution Flow:

- Authenticates with AWS using environment variables
- Provisions t3.small instance in specified subnet
- Configures networking and security groups
- Sets up SSH access with provided key pair

### Dependencies:
- vagrant-aws plugin installed
- AWS credentials in environment variables
- Existing key pair and security groups in AWS
- Valid VPC subnet

## 3. Nginx Configuration (nginx.conf)

### Purpose & Role:
- Load balancer and reverse proxy configuration
- Routes incoming HTTP traffic to Flask application backend

### Configuration Components:

#### 1. Upstream Backend Definition
- Single server: flask-app:5000
- Ready for horizontal scaling (additional servers can be added)

#### 2. Server Block
- Listens on port 80 for HTTP traffic
- Proxies all requests to Flask backend
- Preserves client IP headers for request tracing

#### Proxy Behavior:
- Passes through original Host header
- Adds X-Real-IP with client's actual IP
- Includes X-Forwarded-For for proxy chain tracking
- Maintains request integrity through proxy chain

#### Scalability Ready:
- Current: Single Flask instance
- Scalable: Add multiple servers to upstream for load balancing
- Can implement load balancing algorithms (round-robin, least_conn, etc.)

## 4. Nginx Dockerfile

### Purpose & Role:

- Custom Nginx image builder
- Deploys custom configuration into official Nginx image

### Build Process:
- Starts from official nginx:alpine base image
- Copies custom nginx.conf to replace default configuration
- Creates lightweight, customized Nginx container

### Image Characteristics:
- Based on Alpine Linux (minimal footprint)
- Contains only the custom proxy configuration
- Ready for immediate deployment in Docker Compose stack

## 5. Docker Compose Stack (docker-compose.yml)

### Purpose & Role:
- Multi-container application definition
- Service orchestration for Flask app, PostgreSQL, and Nginx

### Service Architecture:

#### 1. Flask Application Service
- Builds from ./app directory context
- Uses environment variables from external file
- Health-check dependency on PostgreSQL
- Volume mounts for development (live code reload)

#### 2. PostgreSQL Database Service
- Official Postgres 15 image
- Persistent volume for data storage
- Health checks using pg_isready
- Port 5432 exposed for external connections

#### 3. Nginx Load Balancer Service
- Alpine-based lightweight image
- Custom configuration mounted as volume
- Port 80 exposed for web traffic
- Dependency on Flask app service

### Docker Compose Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx (80)    │    │  Flask API(5000)│    │ PostgreSQL(5432)│
│   Load Balancer │────│   REST API      │────│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        ↑                       ↑                       ↑
        │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                       │
└─────────────────────────────────────────────────────────────────┘

```

### Service Relationships:

```text
Nginx (Port 80) → Flask App (Port 5000) → PostgreSQL (Port 5432)
```

### Key Features:
- Environment variable injection via external file
- Container health monitoring
- Automatic restart policies
- Persistent data volume for database
## System Architecture Summary

### Deployment Flow:
- Vagrant → Provisions AWS EC2 instance
- Provisioning Script → Installs Docker and dependencies
- Docker Compose → Orchestrates multi-container deployment
- Nginx → Routes traffic to Flask application
- Flask App → Processes requests with PostgreSQL backend

### Network Exposure:
- External: Port 80 (Nginx) on AWS instance
- Internal: Container network between services
- Database: Port 5432 exposed for management access

### Current Limitations:
- Single Flask instance (no load balancing between multiple app instances)
- Basic Nginx configuration without advanced routing rules
- Development-focused volume mounts in production setup
