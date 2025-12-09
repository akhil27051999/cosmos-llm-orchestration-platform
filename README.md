# RESTful API Webserver Application

## 🛠️ Tech Stack & Tools

<p align="left">

<!-- Programming -->
<img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white" alt="Flask" />
<img src="https://img.shields.io/badge/Shell_Scripting-121011?logo=gnu-bash&logoColor=white" alt="Shell Script" />

<!-- Containers & DevOps -->
<img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker" />
<img src="https://img.shields.io/badge/Docker--Compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
<img src="https://img.shields.io/badge/Vagrant-1563FF?logo=vagrant&logoColor=white" alt="Vagrant" />
<img src="https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white" alt="Kubernetes" />
<img src="https://img.shields.io/badge/Helm-0F1689?logo=helm&logoColor=white" alt="Helm" />
<img src="https://img.shields.io/badge/ArgoCD-EF7B4D?logo=argo&logoColor=white" alt="ArgoCD" />

<!-- CI/CD -->
<img src="https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white" alt="GitHub Actions" />
<img src="https://img.shields.io/badge/Makefile-000000?logo=gnu&logoColor=white" alt="Makefile" />

<!-- Monitoring & Observability -->
<img src="https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white" alt="Prometheus" />
<img src="https://img.shields.io/badge/Blackbox_Exporter-000000?logo=prometheus&logoColor=white" alt="Blackbox Exporter" />
<img src="https://img.shields.io/badge/DB_Exporter-316192?logo=postgresql&logoColor=white" alt="DB Exporter" />
<img src="https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white" alt="Grafana" />
<img src="https://img.shields.io/badge/Loki-4c8b64?logo=grafana&logoColor=white" alt="Loki" />
<img src="https://img.shields.io/badge/Alertmanager-E6522C?logo=prometheus&logoColor=white" alt="Alertmanager" />

<!-- Databases -->
<img src="https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />

<!-- API & Tools -->
<img src="https://img.shields.io/badge/Postman-FF6C37?logo=postman&logoColor=white" alt="Postman" />

</p>

## Overview

This repository contains a Student CRUD (Create, Read, Update, Delete) REST API built with Python and the Flask web framework. The project is a comprehensive showcase of modern DevOps practices, demonstrating everything from local development and containerization to CI/CD and deployment on both bare-metal and Kubernetes environments.

The API adheres to RESTful design principles and the Twelve-Factor App methodology:
-   **Versioning**: All endpoints are versioned (e.g., `/api/v1/students`).
-   **Correct HTTP Methods**: `POST`, `GET`, `PUT`, and `DELETE` are used for their intended CRUD operations.
-   **Logging**: Structured and meaningful logs are emitted with appropriate log levels.
-   **Health Check**: A `/health` endpoint is provided to monitor API status.
-   **Unit Testing**: Endpoints are covered by unit tests to ensure reliability.

## Project Prerequisites

- **Create a project folder and a .venv folder within:**
  ```sh
  mkdir myproject && cd myproject
  ```

- **Install python3-venv:**
  ```sh
  sudo apt update
  sudo apt install python3-venv python3-pip
  ```

- **Create a new virtual environment:**
  ```sh
  python3 -m venv venv
  ```

- **Activate the environment :**
  ```sh
  source venv/bin/activate
  ```  

- **Verify Python and pip installation:**
  ```sh
  python3 --version
  pip --version
  ```

- **Within the activated environment, use the following command to install tools:**
  ```sh
  pip install Flask Flask-SQLAlchemy Flask-Migrate python-dotenv pytest
  ```  

- **To verify and list the installations :**
  ```sh
  python3 --version && pip list
  ```

- **copy the dependencies to requirements.txt :**
  ```sh
  pip freeze > requirements.txt
  ```

## Project local setup

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

**At the end: "Every commit to main will test your code and publish a Docker image"**

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
- **At the end: "we’ll have a mini production setup with scaling + load balancing".**

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

**At the end: "we have a real K8s cluster with node roles".**

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
  
**At the end: "Our app is cloud-ready, secure, and scalable on Kubernetes".**
