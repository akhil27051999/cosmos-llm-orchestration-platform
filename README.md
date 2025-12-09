# RESTful API Webserver Application
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/akhil27051999/RESTful-API-Webserver-Application)

## Overview

This repository contains a Student CRUD (Create, Read, Update, Delete) REST API built with Python and the Flask web framework. The project is a comprehensive showcase of modern DevOps practices, demonstrating everything from local development and containerization to CI/CD and deployment on both bare-metal and Kubernetes environments.

The API adheres to RESTful design principles and the Twelve-Factor App methodology:
-   **Versioning**: All endpoints are versioned (e.g., `/api/v1/students`).
-   **Correct HTTP Methods**: `POST`, `GET`, `PUT`, and `DELETE` are used for their intended CRUD operations.
-   **Logging**: Structured and meaningful logs are emitted with appropriate log levels.
-   **Health Check**: A `/health` endpoint is provided to monitor API status.
-   **Unit Testing**: Endpoints are covered by unit tests to ensure reliability.

## Prerequisites

Before running the project locally, ensure your system is set up with a Python virtual environment.

1.  **Install Python `venv` and `pip`:**
    ```sh
    sudo apt update
    sudo apt install python3-venv python3-pip
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install project dependencies:**
    ```sh
    pip install -r app/requirements.txt
    ```

## Local Development

The `Makefile` provides convenient shortcuts for common development tasks.

1.  **Install dependencies:**
    ```sh
    make install
    ```

2.  **Run the application:**
    ```sh
    make run
    ```
    The Flask application will be available at `http://127.0.0.1:5000`.

3.  **Run unit tests:**
    ```sh
    make test
    ```

## Containerization with Docker

The application is containerized following Docker best practices, including multi-stage builds to reduce image size from 1.26GB to 110MB (a ~91% reduction).

1.  **Build the Docker image:**
    ```sh
    make docker-build DOCKER_IMAGE_TAG=1.0.1
    ```

2.  **Run the Docker container:**
    ```sh
    make docker-run DOCKER_IMAGE_TAG=1.0.1
    ```
    The API will be available at `http://localhost:5000`.

3.  **View container logs:**
    ```sh
    make docker-logs
    ```

4.  **Stop and remove the container:**
    ```sh
    make docker-stop
    ```

5.  **Remove the Docker image:**
    ```sh
    make docker-clean
    ```

## Local Multi-Container Setup with Docker Compose

A `docker-compose.yaml` file is provided to orchestrate the Flask API, PostgreSQL database, and an Nginx reverse proxy for a one-click local development setup.

1.  **Start the services:**
    ```sh
    make compose-up
    ```

2.  **Run database migrations:**
    After starting the containers, create the database tables by running migrations.
    ```sh
    make migrate
    ```

3.  **Seed the database (Optional):**
    Populate the database with initial dummy data.
    ```sh
    make seed
    ```

4.  **Stop and clean up all services:**
    This command stops the containers and removes the associated volumes.
    ```sh
    make compose-down
    ```

## CI/CD Pipeline with GitHub Actions

A CI pipeline is configured using GitHub Actions (`.github/workflows/ci-pipeline.yaml`) to automate the build, test, and publish process.

**Pipeline Stages:**
1.  **Build & Test**: Checks out code and runs unit tests.
2.  **Docker Build & Push**: Builds the Docker image, tags it with the Git SHA, and pushes it to Docker Hub.
3.  **Update Helm Chart**: Automatically updates the `image.tag` in the Helm chart (`helm/application/values.yaml`) and pushes the change back to the repository, enabling GitOps workflows.

**Triggers:**
-   On push or pull request to the `dev` or `main` branches affecting the `app/` directory.
-   Manual trigger via `workflow_dispatch`.

## Infrastructure as Code

### Terraform
The `terraform/` directory contains configurations to provision the necessary AWS infrastructure, including a VPC, subnets, EC2 instance, security groups, and IAM roles. This automates the setup of the underlying environment for deployment.

### Ansible
The `ansible/` directory contains playbooks designed to bootstrap a fresh VM. The playbook installs and configures a complete DevOps toolset, including Docker, Kubernetes tools (kubectl, minikube), Terraform, and more, making the machine ready for deployment and management tasks.

## Deployment

### Kubernetes Cluster Setup (Minikube)

A local 3-node Kubernetes cluster can be provisioned using Minikube to simulate a production-like environment.

1.  **Start the 3-node cluster:**
    ```sh
    minikube start --nodes 3
    ```
2.  **Label nodes for workload separation:**
    This isolates application, database, and dependency workloads onto different nodes.
    ```sh
    kubectl label node minikube type=application
    kubectl label node minikube-m02 type=database
    kubectl label node minikube-m03 type=dependent_services
    ```

### Kubernetes Deployment with Helm and ArgoCD

The entire application stack, including the API, database, and monitoring tools, is packaged as Helm charts located in the `helm/` directory. ArgoCD is used for GitOps-style continuous deployment.

1.  **Deploy Application Stack using Manifests:**
    The Kubernetes manifests in the `k8s/` directory can be used for direct deployment.
    ```sh
    # Deploy Vault for secret management
    kubectl apply -f k8s/vault.yaml
    
    # Deploy External Secrets Operator
    envsubst < k8s/external-secrets.yaml | kubectl apply -f -

    # Deploy Database (Postgres)
    kubectl apply -f k8s/database.yaml

    # Deploy Application (Flask API)
    kubectl apply -f k8s/application.yaml
    ```
2.  **Deploy using ArgoCD:**
    The `argocd/` directory contains Application definitions to deploy the Helm charts via a GitOps workflow. Once ArgoCD is set up, it will monitor the Git repository and automatically sync the cluster state with the chart definitions.

### Key Deployment Concepts:
-   **Helm Charts**: For templatized, repeatable deployments.
-   **Init Containers**: Used in the application deployment to run database migrations before the main container starts.
-   **ConfigMaps**: To manage non-sensitive configuration like database host and port.
-   **Secrets Management**: HashiCorp Vault, coupled with the External Secrets Operator (ESO), is used to securely inject database credentials and other secrets into pods.
-   **Observability**: The stack includes configurations for Prometheus, Grafana, Loki, and Promtail for monitoring, metrics, and log aggregation.
-   **Postman Collection**: A Postman collection is available at `postman/` for testing the API endpoints.

### Verifying the Deployment

-   **Check Pods:**
    ```sh
    kubectl get pods -n student-api
    ```
-   **Access the API:**
    Port-forward the service to access it locally.
    ```sh
    kubectl port-forward svc/flask-api-service 8080:80 -n student-api
    ```
    The API is now accessible at `http://localhost:8080/students`.

-   **Clean up resources:**
    ```sh
    kubectl delete -f k8s/application.yml
    kubectl delete -f k8s/database.yml
    kubectl delete -f k8s/vault.yml
    kubectl delete -f k8s/external-secrets.yml

  # Simple REST API Webserver

### Overview: 
**Created a Student CRUD REST API using python programming language and Flask web framework.
With this we can able to:**
- `Create`: Add a new student.
- `Read` (All): Retrieve a list of all students.
- `Read` (One): Retrieve details of a specific student by ID.
- `Update`: Modify existing student information.
- `Delete`: Remove a student record by ID.

## Purpose of the Repo

**The following RESTful design principles and standards were implemented with the help of `Twelve Factor App` and `Best Practices for REST API Design`**

- **Versioning:**

  All endpoints are versioned:
    e.g., /api/v1/students

- **HTTP Methods Used Correctly:**
  - POST – Create a new student
  - GET – Fetch student(s)
  - PUT – Update student information
  - DELETE – Remove a student

- **Logging:**

  Meaningful and structured logs are emitted with appropriate log levels (INFO, WARNING, ERROR).

- **Health Check Endpoint:**

  A dedicated /api/v1/healthcheck endpoint is available to verify the API's availability and status.

- **Unit Testing:**

  Each endpoint is covered by unit tests to ensure proper functionality and error handling.


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
