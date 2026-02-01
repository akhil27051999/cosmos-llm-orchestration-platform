# DEVOPSIFY REST API WEBSERVER

### Overview

This repository contains a Student CRUD (Create, Read, Update, Delete) REST API built with Python and the Flask web framework. The project is a comprehensive showcase of modern DevOps practices, demonstrating everything from local development and containerization to CI/CD and deployment on both bare-metal and Kubernetes environments.

#### Designed and DevOpsified a RESTful API application using tools:

```txt
- Application Design Language : Python + Flask Framework
- Database                    : Postgres Database
- Automation Scripts          : Bash / Shell Scripting
- Infrastructure as Code      : Terraform
- Configuration Management    : Ansible
- Version Control Filesystem  : Git
- Containerization            : Docker with Dockerfile creation
- Container Registry          : Dockerhub
- One Click Local Setup       : Docker compose; Makefile
- Container Orchestration     : Kubernetes with Three node Cluster
- Continuous Integration (CI) : GitHub Actions + Self Hosted Runners
- Continuous Deployment (CD)  : ArgoCD with Helm Charts
- Monitoring & Observability  : Prometheus, Grafana, Loki (PLG Stack)
- Cloud                       : AWS 
```
#### AWS Services used
```txt
- Compute                    : EC2 t3.xlarge instance
- Networking                 : VPC, Subnets, Route Tables (RT), NAT Gateways (NAT-GW), Internet Gateways (IGW)
- IAM & Security             : IAM (Users, Groups, Roles & Permissions), RBAC, Security Groups
- Storage & Databases        : EBS Instance Storage, S3 bucket for Static file storage, Relation Databases(RDS)
- Resource Monitoring        : AWS CloudWatch, AWS Cloud-Trail
```

## REST API Application Design

### I. Project Prerequisites Setup

#### 1. Create a public repository on GitHub and clone the repository into the local.
#### 2. Install the Prerequisites tools and softwares: `Python 3.8+` or above version; `Git`; `PostgresDB` in our local.
#### 3. Create and activate the virtual environment using
  
  ```py
   python3 -m venv .venv
   source .venv/bin/activate
  ```
#### 4. Install the required packages using:

  ```sh
pip install Flask Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-dotenv pytest pytest-flask pytest-dotenv gunicorn
  ```

#### 5. verify and freeze the dependencies
  ```sh
  pip list
  pip freeze > requirements.txt 
  ```

#### 6. Version Control Filesystem setup: Git

  ```sh
  # Initialize git 
    git init 

  # Add and commit the files to git
    git add requirements.txt
    git commit -m "required packages for designing RESTful API" 
  
  # Add remote origin
    git remote add origin https://github.com/akhil27051999/Flask-REST-API.git

  # Rename default branch to main
    git branch -M main

  # Push to GitHub
    git push -u origin main
  ```

**7. Create `.gitignore` file to avoild git from tracking files that are not required.**

---

### II. Postgres Database Setup

#### 1. Install and verify PostgreSQL

  ```sh
  # Update and Install postgresql package in local
    sudo apt update && sudo apt install postgresql postgresql-contrib

  # Check if PostgreSQL is running
    sudo systemctl status postgresql
  
  # If not running, start the service
    sudo systemctl start postgresql

  # Enable PostgreSQL to start on boot
    sudo systemctl enable postgresql
  ```

#### 2. PostgresDB Configuration
  
  ```sh
  # Access Postgresdb Shell
    sudo -u postgres psql
  
  # List all users
    sudo -u postgres psql -c "\du"
  
  # List all databases
    sudo -u postgres psql -c "\l"
  
  # Test connection with created user (prompts for password)
    psql -U student_user -d studentdb -h localhost -W
  
  # Or connect directly as postgres user
    sudo -u postgres psql -d studentdb

  -- Create a new user with password
    CREATE USER postgres WITH PASSWORD 'postgres123';
  
  -- Alternative: Use existing postgres user with new password
    ALTER USER postgres WITH PASSWORD 'postgres123';

  -- Create database for the application
    CREATE DATABASE studentdb;
  
  -- Grant privileges to the user
    GRANT ALL PRIVILEGES ON DATABASE studentdb TO postgres;
  
  -- Make the user the owner of the database (optional)
    ALTER DATABASE studentdb OWNER TO postgres;

  -- Connect to specific database
    \c studentdb
  
  -- List all tables
    \dt
  
  -- Describe table structure
    \d students

  -- View table data
    SELECT * FROM students;

  -- Exit PostgreSQL shell
    \q
  ```

---

### III. App File Structure Setup

#### 1. Create a `.env` file 
  - To store the credentials of `postgresdb` in local 
  - ***Note*** : Don't commit the `.env` into github, use `.gitignore` file to untrack the file by commiting into git.

#### 2. Create a `config.py` file 
  - For best practice to load configs like `user & db credentials` and `database URL's` into the application without hardcoding them directly into the application.
  - Use python libraries like `dotenv` to load the `.env` file from our local into the app code.
  - Make sure we install `psycopg2-binary` adapter to connect our `REST API` app with `postgresdb` service running in our local.
  - Also we can use `Secrets Managers` like `Hashicorp Vault` / `AWS Secret Manager` to store secrets and use them for applications running in production.

#### 3. Create `models.py` file
  - `models.py` is where we define the structure of our database using Python classes instead of writing SQL.
    - Each model = one database table
    - Each class attribute = one table column
  - Use `SQLAlchemy` library, models are Python class representations of database tables. They define the schema, relationships, and constraints in one place, allowing the ORM to generate SQL, manage migrations, and let us interact with the database using Python objects instead of raw SQL.

#### 4. Create `routes.py` file

  - File that defines all `CRUD` (`Create`, `Read`, `Update`, `Delete`) API endpoints related to Student management using Flask Blueprints.
  - It separates routing logic from application setup, following clean architecture principles.
    - Define `RESTful endpoints` for students
    - Handle `HTTP requests and responses`
    - Interact with the database using `SQLAlchemy models`
    - Perform `basic validation` and `error handling`

#### 5. Create `loggers.py` file
  - File to configures a centralized logging system that writes structured logs to both the `console` and a `persistent log file`, ensuring consistent, duplicate-free logging across the entire Flask application.
    - Provide a reusable logging configuration
    - Enable structured and timestamped logs
    - Write logs to a `persistent file` for `debugging` and `audits`
    - Prevent duplicate log entries
    - Integrate seamlessly with Flask’s built-in logger

#### 6. Create `__init__.py` file

  - App Factory file initializes the Flask application using the application factory pattern:
    - registers `models` and `routes`
    - configures `logging`, `database`, and `migrations`
    - Exposes `basic health` and `home` endpoints for the Student Management API.

---

### IV. Database Migration

- Requires `Flask-Migrate` installed and `FLASK_APP` set.
  - Set `FLASK_APP` and initialize migrations:

  ```sh
  # Set the flask app entrypoint (Mac/Linux)
    export FLASK_APP=app:create_app
  
  # Initialize migrations (run once)
    flask db init
  
  # Generate migration after creating models
    flask db migrate -m "Initial migration - create students table"
  
  # Apply migrations to the DB
    flask db upgrade
  ```
  - Migration folder structure after flask db init:

  ```sh
  migrations/
  ├── versions/           # Individual migration scripts
  ├── env.py              # Alembic environment configuration
  └── script.py.mako      # Migration script template
  ```

  ### Other common migration commands:

  ```sh
  # rollback last migration
    flask db downgrade
  
  # show current migration revision
    flask db current
  
  # show migration history
    flask db history
  ```
---

### V. Common Troubleshooting Issues

  - Connection Issues
  ```sh
  # Check if PostgreSQL is listening on correct port
    sudo netstat -tulpn | grep 5432
  ```
  - Check PostgreSQL logs
  ```sh
  sudo tail -f /var/log/postgresql/postgresql-*.log
  ```
  - Permission Issues - If you face permission problems, run in psql as a superuser:
  ```sh
  GRANT ALL ON SCHEMA public TO student_user;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO student_user;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO student_user;
  ```
  - Reset PostgreSQL Password
  ```sql
  -- If you forget the postgres user password:
    ALTER USER postgres WITH PASSWORD 'new_password';
  ```
---

### VI. Database Seeding Script (seed.py)

  - This script is used to populate the database with sample 100 student records for development and testing purposes.
  - It creates realistic dummy data and inserts it efficiently using SQLAlchemy.
    - Seed the database with test data
    - Simplify local development and testing
    - Avoid manual data entry
    - Quickly validate API endpoints and queries

---

### VII. Postman Testing Best Practices

**Pre-requisites:**
- Flask app running on `localhost:5000`
- PostgreSQL running and connected
- Migrations applied (`flask db upgrade`)
- Virtual environment activated

**Test data management:**
- Use unique emails per test.
- Clean up test data after runs (or use disposable test DB).
- Consider automated `Postman tests` and a CI job to run them against a staging environment.

**Postman tips:**
- Put requests into a `Collection` and group by `resource`.
- Use Environment variables (e.g., `base_url`, `student_id`) to make requests portable.
- Add Tests in Postman to assert `response codes` and `JSON structure`.
- Use pre-request scripts to dynamically set `student_id` from response data.

**Common issues:**
- `Connection refused` — Ensure Flask app is running and listening on port `5000`.
- `DB errors` — confirm Postgres is running, credentials and `DATABASE_URL` are correct.
- `404 errors` — check URL and `student_id`.
- `Validation errors` — ensure Content-Type header and JSON payloads are correct.

---

### VIII. Load Testing observation

- `API Stability`: All core endpoints remained stable under concurrent load, with lightweight endpoints `(/ and /health)` consistently responding `fast and without failures`.
- `Read Performance`: `GET /students` handled moderate concurrency well but showed `increased latency` at `higher record counts` due to large response payloads, indicating a need for pagination in production.
- `Write Performance`: `POST /students` throughput was `lower compared to reads`, with `failures caused mainly by unique email constraints`, highlighting the importance of `unique test data and write optimization`.
- `Overall Results`: The API achieved `~32–35` `requests/sec` aggregate throughput, demonstrated strong performance for read-heavy workloads, and remained reliable under mixed traffic patterns.


## Project local setup using Makefile

**1. Install dependencies**
  ```txt
  make install
  ```
  - (or run pip install -r requirements.txt directly)

**2. Run the App**
  ```txt
  make run
  ```

**3. Flask app will start at:**
  ```url
  http://127.0.0.1:5000
  ```

  - Endpoints:
    - / → Welcome message
    - /health → Health check
    - /students → Manage students
      
**4. Run all unit tests:**
  ```txt
  make test
  ```
  Or directly:

  ```txt
  pytest -v
  ```

## Containerising the REST API

### Containerised REST API with the Docker best practices and reduced both Size and Build Time of my Docker Image:
  - Used `python:3.10-alpine` for base image which resulted in reducing the image size because of it's lightweight version that supports the build process without impacting it's functionality. as a resultant the application image size reduced from `1.26GB` to `176MB`.

  - Followed Multi-stage Dockerfile method, this helped to reduce the image size from `176MB` to `110MB`, This approach ensures that only the essential runtime files are included in the final image, reducing size and improving performance.

  - Overall I managed to reduce the original `1.26GB` image to just `110MB`, achieving a `91.27%` size decrease while maintaining the same functionality and improving rebuild times by an average of 20 seconds.

### Docker Commands

**1. Build the Docker Image:**

  - Built the image with semantic versioning tags:
  ```sh
  make docker-build DOCKER_IMAGE_TAG=1.0.1
  ```

  or directly with Docker:
  ```sh
  docker build -f app/Dockerfile -t ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG} .
  ```
  - We can change the `DOCKER_IMAGE_TAG` to any version.

**2. Run the Docker Container:**
  - Run the container 
  ```sh
  make docker-run DOCKER_IMAGE_TAG=1.0.1
  ```
  or directly with Docker:

  ```sh
  docker run -d --env-file .env -p 5000:5000 ${DOCKER_CONTAINER} ${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}
  ```
  - Now the API will be available at:
  ```url
  http://localhost:5000
  ```

**3. To Remove the Containers:**
  - To remove the containers using make command
  ```sh
  make docker-stop
  ```

  or directly with Docker:

  ```sh 
  docker stop ${DOCKER_CONTAINER}
  docker rm ${DOCKER_CONTAINER}
  ```

**4. To Remove the unused images:**
  - To remove the images using make command
  ```sh
  make docker-clean
  ```

  or directly with Docker:

  ```sh
  docker rmi ${DOCKER_IMAGE}:${DOCKER_IMAGE_TAG}
  ```

**5. For Troubleshooting Container issue:**
  - To check container logs using make command
  ```sh
  make docker logs
  ```
  or directly with Docker:

  ```sh
  docker logs -f ${DOCKER_CONTAINER}
  ```
  
## One click local development setup

**Created docker-compose.yml file to containerise Flask (API) and Postgres (DB) together, with persistent volumes for one click local development setup.**

### Docker Compose Commands

**1. To start the service stack**
  ```sh
  docker compose up -d --build
  ```
  or 

  ```txt
  make up
  ```

**2. To stop and remove everything (including volumes)**
  ```sh
  docker compose down -v
  ```

  or 

  ```txt
  make down
  ```

### For Database Migration & Seeding
**After starting the containers, you need to run migrations (to create tables) and optionally seed data.**

**1. Apply migrations inside the Flask container**
  ```sh
  docker exec -it flask-container flask db upgrade
  ```

  or 

  ```txt
  make migrate
  ```

**2. To Seed the database with initial data**
  ```sh
  docker exec -it flask-container python seed.py
  ```

  or 

  ```txt
  make seed
  ```

**3. Verify Database**

- To connect into the Postgres container
  ```sh
  docker exec -it postgres-container psql -U postgres -d studentdb
  ```

- Then inside psql:
  ```sql
  \dt           -- list tables
  SELECT * FROM students LIMIT 5;
  ```

**4. To Run API container (depends on DB + migrations + seed)**

  ```txt
  make run
  ```

### API Endpoints

- Once containers are up, the API will be available at:

  http://localhost:5000/students

  http://localhost:5000/health


## Setup CI pipeline

**Automation for build, test, and publish of Docker images using GitHub Actions workflow for CI pipeline**

### pipeline stages
- Build API → make sure it compiles.
- Run tests → unit tests should pass.
- Lint → run flake8/pylint/eslint.
- Docker login → authenticate to registry (DockerHub/GHCR).
- Docker build & push → push tagged image.

### Triggering

- Automatically when changes are made inside /api/**.
- Manual trigger (workflow_dispatch).

### Self-hosted runner
- GitHub Actions running on our laptop/VM to simulate real-world self-hosted CI.

`At the end`: "Every commit to main will test your code and publish a Docker image"

## Deploy on Bare Metal
**To deploy on a “production-like” environment without Kubernetes — just Docker + Nginx on a Vagrant box.**

### Key Points

- Vagrantfile creates a VM (e.g., Ubuntu).
- A provisioning script installs Docker, Docker Compose, Nginx.
- docker-compose.yml deploys:
  - 2 API containers (scale with replicas).
  - 1 Postgres DB container.
  - 1 Nginx container (load balances API replicas).

### Nginx config

```nginx
upstream api_backend {
    server api1:5000;
    server api2:5000;
}
server {
    listen 8080;
    location / {
        proxy_pass http://api_backend;
    }
}
```
- **Access API at http://localhost:8080/api/v1/students.**
`At the end`: "we’ll have a mini production setup with scaling + load balancing".

## Setup Kubernetes Cluster

**Spin up a 3-node Kubernetes cluster with Minikube.**

### Key Points

- **Start minikube with 3 nodes:**
  ```sh
  minikube start --nodes=3
  ```

- **Label nodes:**
  - Node A → type=application
  - Node B → type=database
  - Node C → type=dependent_services

- This enforces workload isolation (apps on one node, DB on another, monitoring tools on another).

### Minikube Cluster setup commands

```sh
# Start a 3-node cluster
minikube start --nodes 3

# Check all nodes
kubectl get nodes -o wide

# Label nodes for workload separation
kubectl label node minikube type=application
kubectl label node minikube-m02 type=database
kubectl label node minikube-m03 type=dependent_services
```

`At the end`: "we have a real K8s cluster with node roles".

## Deploy API, DB and other services in Kubernetes

**Move from Docker Compose → Kubernetes deployment.**

### Key Points

- **Manifests should be modular:**
  - **application.yml** → namespace, configmap, secret, deployment, service for API.
  - **database.yml** → namespace, deployment, service for Postgres.

- **Init container** → runs DB migrations before starting API.
- **ConfigMaps** → non-sensitive configs (e.g., DB host).
- **Secrets** → sensitive info (DB password).
- **External Secrets Operator + Vault** → manage secrets properly.
- **Services** →
  - ClusterIP for DB (internal only).
  - NodePort/LoadBalancer for API (external access).
- **Namespace isolation** → student-api for app + db, others for observability.
- **Test via Postman**: all endpoints should work and return 200.

### K8s deployment and verification commands

- **Deploy API + DB**
  ```sh
  kubectl apply -f k8s/database.yml
  kubectl apply -f k8s/application.yml
  ```

- **Deploy Vault + ESO**
  ```sh
  kubectl apply -f k8s/vault.yml
  kubectl apply -f k8s/external-secrets.yml
  ```
- **Verify Deployments**
  ```sh
  # Check namespaces
  kubectl get ns

  # Check pods
  kubectl get pods -n student-api

  # Check deployments
  kubectl get deployments -n student-api

  # Check services
  kubectl get svc -n student-api
  ```
- **Debugging**
  ```sh
  # Describe pod for events/logs
  kubectl describe pod <pod-name> -n student-api

  # View container logs
  kubectl logs -f <pod-name> -n student-api

  # Exec into a running pod
  kubectl exec -it <pod-name> -n student-api -- /bin/sh
  ```
- **Port Forward (if no LoadBalancer)**
  ```sh
  kubectl port-forward svc/student-api-service 8080:80 -n student-api
  ```
  - Now access API at: **http://localhost:8080/api/v1/students**

- **Testing in Kubernetes**
  ```sh
  # Healthcheck endpoint
  curl http://<node-ip>:<nodePort>/healthcheck
  ```
  - Expected response:
  ```json
  {"status": "ok"}
  ```

- **Cleanup**
  ```sh
  kubectl delete -f k8s/application.yml
  kubectl delete -f k8s/database.yml
  kubectl delete -f k8s/vault.yml
  kubectl delete -f k8s/external-secrets.yml
  ```
  
`At the end`: "Our app is cloud-ready, secure, and scalable on Kubernetes".

## Helm-Based Deployments (Commands + Notes)

All repository Helm charts live in `/helm`. Charts included:
- helm/student-api (application chart)
- helm/postgres (postgres chart — can be community chart copied)
- helm/vault (vault chart)
- helm/prometheus, helm/loki, helm/grafana, helm/promtail, etc.

Create namespace:
```bash
kubectl create ns student-api || true
```

Install API chart:
```bash
helm install student-api helm/student-api -n student-api
```

Install DB chart:
```bash
helm install student-db helm/postgres -n student-api
```

Notes:
- Use `values.yaml` to override image tag, replicas, env vars, service type.
- DB migrations are triggered by the API chart using an initContainer (ensure initContainer has DB connection and credentials).
- To pass secrets, use sealed-secrets/ExternalSecrets/Vault integration — do not put secrets in values.yaml in plaintext.

Upgrade after changes (code or chart values):
```bash
helm upgrade student-api helm/student-api -n student-api
```

Uninstall:
```bash
helm uninstall student-api -n student-api
helm uninstall student-db -n student-api
```

Verify pods:
```bash
kubectl get pods -n student-api
```

Test API:
```bash
# If NodePort or LoadBalancer available, hit the external IP; otherwise port-forward
curl http://<NODE-IP>:<NODEPORT>/api/v1/students
# or
kubectl port-forward svc/student-api-service 8080:80 -n student-api
curl http://localhost:8080/api/v1/students
```

Best practices:
- Keep values.yaml minimal; environment-specific overrides via `values.prod.yaml`.
- Use imagePullSecrets for private registries.
- Use probes (liveness/readiness) for reliable rollouts.

`At the end`: Our entire stack is deployed declaratively using Helm templates, enabling repeatable, scalable deployments.

---

## GitOps with ArgoCD (Commands + Notes)

Install ArgoCD (apply manifests in repository):
```bash
kubectl create ns argocd || true
kubectl apply -f argocd/ -n argocd
```

Port-forward ArgoCD UI:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access UI: https://localhost:8080
```

ArgoCD key points:
- Applications, repo credentials, and projects are stored declaratively under `/argocd/`.
- ArgoCD watches the Helm charts and `values.yaml` changes, then syncs automatically.
- GitHub Actions updates `helm/student-api/values.yaml` (image.tag) after CI build.
- ArgoCD picks up the change and deploys via auto-sync.

Apply ArgoCD resources (if you change them):
```bash
kubectl apply -f argocd/ -n argocd
```

`At the end`: We achieve full GitOps — automated, version-controlled, self-correcting deployments.

---

## Observability Stack (Prometheus, Loki, Grafana, Exporters) — Helm (Commands)

Create observability namespace:
```bash
kubectl create ns observability || true
```

Install components (Helm charts under `helm/` in the repo):
```bash
helm install prometheus helm/prometheus -n observability
helm install loki helm/loki -n observability
helm install promtail helm/promtail -n observability
helm install grafana helm/grafana -n observability
```

Verify:
```bash
kubectl get pods -n observability
```

Grafana access:
```bash
kubectl port-forward svc/grafana -n observability 3000:80
# Open http://localhost:3000
# Default credentials depend on chart (check secret or values)
```

Data sources to configure in Grafana:
- Prometheus
- Loki

Promtail:
- Pulls logs from application pods (via label selectors)
- Ensure promtail's serviceAccount has permissions to read pod logs

`At the end`: Full end-to-end observability for logs + metrics + service uptime.

---

## Dashboards & Alerts (Grafana + Alertmanager + Slack) — Commands & Notes

Dashboards:
- Import or provision dashboards for:
  - DB metrics (Postgres exporter)
  - Application logs (Loki)
  - Node & kube-state metrics
  - Blackbox monitoring (uptime/latency)

Alertmanager Slack integration (example snippet to add to Alertmanager config):
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - channel: '#alerts'
        text: " Alert: {{ .CommonAnnotations.description }}"
```

Apply alert rules (example):
```bash
kubectl apply -f observability/alerts/ -n observability
```

Test alert:
```bash
kubectl apply -f observability/alerts/test-alert.yaml -n observability
```

Common alert conditions:
- CPU > 80% for 5 minutes
- Disk > 85%
- 5xx error spike in 10 minutes
- Latency SLI breaches (p90/p95/p99)
- Pod restart spikes for DB/Vault/ArgoCD

`At the end`: Production-grade observability with alerting to Slack.

---

## Closing Statements

This repository demonstrates a complete development-to-production workflow:
- Local development with virtualenv and Docker Compose
- CI that builds images and updates Helm values
- Declarative deployments using Helm charts
- GitOps delivery using ArgoCD
- Production-grade observability using Prometheus, Loki, and Grafana

Our entire stack is deployed declaratively using Helm templates, enabling repeatable, scalable deployments. We achieve full GitOps — automated, version-controlled, self-correcting deployments. We also provide end-to-end observability and alerts to help operate the system in production.
