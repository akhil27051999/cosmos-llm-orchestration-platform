# Docker for Flask REST API — Complete Implementation Guide

### Overview

This guide covers Docker implementation for a Flask REST API that uses PostgreSQL. It explains how to build efficient, secure, and production-ready Docker images, how to run containers for development and production, and how to troubleshoot common issues.

Key benefits:
- Consistency across environments
- Isolation and portability
- Ease of scaling using container orchestration
---

## Milestone Expectations

### Problem Statement
- Create Dockerfile for the REST API.

### Expectations
**The following expectations should be met to complete this milestone.**
1. API should be run using the docker image.
2. Dockerfile should have different stages to build and run the API.
3. We should be able to inject environment variables while running the docker container at runtime.
4. README.md should be updated with proper instructions to build the image and run the docker container.
5. Similarly appropriate make targets should be added in the Makefile.
6. The docker image should be properly tagged using semver tagging, use of latest tag is heavily discouraged.
7. Appropriate measures should be taken to reduce docker image size. We want our images to have a small size footprint.

---

## Dockerfile Implementation

### Basic Dockerfile (simple, easy to understand)
```dockerfile
# app/Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
```
---

.dockerignore

Place this file next to your Dockerfile to reduce build context and avoid copying secrets.

```text
# ignore virtual env files into git
/venv/*

# ignore environment variable files
.env.dev
.env.prod

# ignore testing environment variable files
.env.test

# ignore Python bytecode files
app/__pycache__/*
__pycache__/
.pytest_cache
*.pyc

# ignore log files
*.log
```

---

### wsgi.py

Example entrypoint used by Gunicorn.

```python
# wsgi.py

from app import create_app
app = create_app()

```

---

## Docker Commands Reference

### Building Images
```bash
# Build with tag
docker build -t student-api:v1.0.0 .

# Build using a specific Dockerfile
docker build -f Dockerfile.prod -t student-api:prod .

# Build with build args
docker build --build-arg ENVIRONMENT=production -t student-api:prod .
```

### Running Containers
```bash
# Basic run (bind host:container)
docker run -p 5000:5000 student-api:v1.0.0

# Run in detached mode
docker run -d -p 5000:5000 --name student-api student-api:v1.0.0

# With environment variables
docker run -d \
  -p 5000:5000 \
  --name student-api \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e FLASK_ENV=production \
  student-api:v1.0.0

# With environment file
docker run -d \
  -p 5000:5000 \
  --name student-api \
  --env-file .env \
  student-api:v1.0.0

# With volume mounting (for logs or persistent data)
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  student-api:v1.0.0
```

### Container Management
```bash
# List running containers
docker ps

# List all containers
docker ps -a

# View container logs
docker logs student-api

# Follow logs
docker logs -f student-api

# Execute a shell in a running container
docker exec -it student-api sh

# Stop container
docker stop student-api

# Remove container
docker rm student-api

# Stop and remove in one command
docker rm -f student-api
```

### Image Management
```bash
# List images
docker images

# Remove an image
docker rmi student-api:v1.0.0

# Remove dangling/unused images
docker image prune

# Remove all unused images
docker image prune -a

# View image history
docker history student-api:v1.0.0

# Inspect image metadata
docker inspect student-api:v1.0.0
```

### System Management
```bash
# Show disk usage
docker system df

# Clean up everything (dangling images, stopped containers)
docker system prune -a

# View system information
docker system info
```

---

## Image Optimization Strategies

**1. Layer Caching**
- Copy and install dependencies before copying the application code to make use of Docker build cache.
  - Good:
    ```
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . .
    ```
  - Bad:
    ```
    COPY . .
    RUN pip install -r requirements.txt
    ```

**2. Use Minimal Base Images**
- Alpine or slim variants reduce image size. Be aware of compatibility (some wheels require build tools).

**3. Install Only Required Packages**
- Avoid installing unnecessary OS packages in the runtime image.

**4. Use --no-cache-dir with pip**
- Prevents caching wheels in the image: `pip install --no-cache-dir -r requirements.txt`

**5. Multi-stage Builds**
- Build dependencies in a builder stage and copy only the installed packages to the runtime image to keep final image small.

**6. .dockerignore**
- Exclude local files, tests, and secrets from the build context to speed up builds and avoid leaking secrets.

---

### Multi-stage Builds

**Why use them?**
- Produce significantly smaller images by excluding build-time dependencies (compilers, headers).
- Improve security by reducing attack surface.
- Separate build artifacts from runtime files.

Simple multi-stage example (already shown above): build stage installs dependencies into /root/.local, runtime stage copies them over and runs as non-root user.

---

## Troubleshooting Guide

### Common issues and checks:

#### 1. Container Fails to Start
- Inspect logs:
  ```bash
  docker logs student-api
  ```
- Run interactive shell to debug:
  ```bash
  docker run -it --rm student-api:v1.0.0 sh
  ```

#### 2. Database Connection Issues
- Exec into container and test network connectivity:
  ```bash
  docker exec -it student-api sh
  # inside container
  ping -c 1 postgres-host
  nc -zv postgres-host 5432
  ```
- Verify environment variables:
  ```bash
  docker exec -it student-api env | grep DATABASE
  ```

#### 3. File Permission Problems
- Check permissions:
  ```bash
  docker exec -it student-api ls -la /app
  ```
- Fix in Dockerfile by setting ownership and running as non-root:
  ```dockerfile
  RUN adduser -D appuser && chown -R appuser:appuser /app
  USER appuser
  ```

#### 4. Port Already in Use
- Find process on host using port 5000:
  ```bash
  sudo lsof -i :5000
  ```
- Run container with alternate host port:
  ```bash
  docker run -p 5001:5000 student-api:v1.0.0
  ```

#### 5. Build Failures
- Build with no cache to ensure a fresh build:
  ```bash
  docker build --no-cache -t student-api:v1.0.0 .
  ```
- Check build context size and .dockerignore to avoid sending large files.

#### Debugging commands:
- Inspect container: `docker inspect student-api`
- Check resource usage: `docker stats student-api`
- Copy files out of container: `docker cp student-api:/app/logs/app.log ./app.log`

---

## Quick Reference Cheat Sheet

### Build and Run
```bash
# Build image
docker build -t myapp:v1 .

# Run container
docker run -p 5000:5000 myapp:v1

# Run with env file
docker run --env-file .env myapp:v1

# Debug container
docker exec -it container_name sh
```

### Maintenance
```bash
# Clean up unused resources
docker system prune

# View logs
docker logs container_name

# Monitor containers
docker stats
```

---

### Best Practices Checklist
- Use multi-stage builds
- Choose minimal base images (alpine/slim)
- Implement layer caching (install deps before copying code)
- Use .dockerignore to limit build context
- Run as non-root user inside container
- Include health checks
- Use semantic version tags for images
- Do not store secrets in images; use secret management
- Scan images for vulnerabilities regularly

# Docker Compose & Makefile Integration - Complete Guide

### Overview
Docker Compose simplifies multi-container application management by defining and running interconnected services with a single configuration file. This guide covers best practices for orchestrating Flask APIs with PostgreSQL and Nginx.

### Key Benefits
1. Single Command Deployment: docker-compose up starts entire application stack
2. Service Discovery: Automatic networking between containers
3. Dependency Management: Controlled startup order with health checks
4. Development Consistency: Identical environments across team members
5. Production Readiness: Easy transition from development to production
---

## Milestone Expectations

### Problem Statement
- We want to simplify the process of setting up API on the local machine for development. The idea is to enable other team members to run the API and its dependent services with the least amount of steps involved in getting this up and running.
- We won’t be assuming that other team members have the required tools already installed on their local. So we will be going one step further and providing them with simple bash functions to install the required tools.

### Expectations
**The following expectations should be met to complete this milestone.**
1. API and its dependent services should be run using docker-compose.
2. Makefile should have the following targets.
   - To start DB container.
   - To run DB DML migrations.
   - To build REST API docker image.
   - To run REST API docker container.
3. README.md file should be updated with instructions
   - To add pre-requisites for any existing tools that must already be installed (e.g., docker, make, etc
   - To run different make targets and the order of execution.
4. When we run the make target to start the REST API docker container,
   - It should first start the DB and run DB DML migrations.
   - (Good to have) You can even include checks to see if the DB is already running and DB migrations are already applied.
   - Later it should invoke the docker compose command to start the API docker container.
---

## Docker Compose Architecture

### Application Stack

```text
┌─────────────────┐    ┌─────────────────┐
│  Flask API(5000)│    │ PostgreSQL(5432)│
│   REST API      │────│   Database      │
└─────────────────┘    └─────────────────┘
        ↑                       ↑
        │                       │
┌────────────────────────────────────────┐
│     Docker Compose Network             │
└────────────────────────────────────────┘

```
### File Structure
```text
project/
├── docker-compose.yml
├── .env
├── Makefile
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
└── scripts/
    └── init-db.sh
```
## Complete Docker Compose Setup

### Docker Compose Best Practices

- **Service Isolation**: Define each component (API, DB, web server) as a separate service for modular development and easy scaling.
- **Environment Variables**: Use `env_file` or environment variables for secrets/configs (never hardcode).
- **Volumes**: Persist data by mounting volumes, especially for databases.
- **Healthchecks**: Use healthchecks to ensure services (like Postgres) are ready before dependent services start.
- **depends_on**: Use `depends_on` with healthcheck conditions to control service startup order.
- **Restart Policies**: Always set `restart: always` for production, ensuring services recover from crashes.
- **Minimal Images**: Use official, minimal images (e.g., `python:alpine`, `nginx:alpine`, `postgres:15`) for efficiency.
- **Configuration Management**: Mount config files (e.g., Nginx) as read-only volumes.
- **Clean Networking**: Compose automatically creates a network for your project; services can reference each other by name.
- **Resource Limits**: For production, set CPU/memory limits (not shown here).
- **Version Pinning**: Use explicit image versions to avoid unexpected changes.

### Service Breakdown

#### **flask-app**:
  - Builds from Dockerfile in `./app`, tags as `flask-app:1.0.0`.
  - Uses environment variables from `.env`.
  - Depends on healthy Postgres service.
  - Mounts project directory for code sharing/hot reload (dev mode).
    
#### **postgres**:
  - Uses official Postgres 15 image.
  - Persists data with `pgdata` volume.
  - Reads environment from `.env`.
  - Healthcheck ensures DB is ready before API starts.
  - Exposes port 5432 for local access.

### Environment Configuration (.env.dev)
- Before the deployment export the env file
  
---

## Docker Compose Commands

#### **Build and Start Services**

```sh
# Build all services (API, DB, Nginx)
docker-compose build

# Start all services in foreground
docker-compose up

# Start all services in detached mode (recommended)
docker-compose up -d
```

#### **Stop and Remove Services**

```sh
# Stop and remove all running containers, networks, and volumes defined in the compose file
docker-compose down

# Stop only the running containers (does not remove networks/volumes)
docker-compose stop

# Remove stopped service containers
docker-compose rm <service>
```

#### **Service Management**

```sh
# List running containers and their status
docker-compose ps

# Restart a specific service
docker-compose restart flask-app
```

#### **Logs and Debugging**

```sh
# View logs for all services
docker-compose logs

# View logs for a specific service
docker-compose logs postgres
```

#### **Accessing Containers**

```sh
# Start a shell in a running container
docker-compose exec flask-app /bin/sh

# Run a command inside a service (e.g., database migration)
docker-compose run flask-app flask db upgrade
```

#### **Build/Start Specific Services**

```sh
# Build only the flask-app image
docker-compose build flask-app

# Start only the postgres service
docker-compose up postgres
```

#### **Clean Up Volumes**

```sh
# Stop and remove all containers, networks, and volumes
docker-compose down -v
```

#### Database Commands (Inside Container)

```sh
# Connect to PostgreSQL from inside the container
docker-compose exec postgres psql -U <user> -d <db>
```

#### Maintenance & Troubleshooting

```sh
# Check environment variables inside a running container
docker-compose exec flask-app env

# Remove unused images, containers, and networks
docker system prune -a
```
---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Issues
```bash
# Check if PostgreSQL is healthy
make status

# Test database connectivity
make db-shell

# Check database logs
docker-compose logs postgres

# Verify environment variables
docker-compose exec flask-app env | grep DATABASE
```

#### 2. Application Startup Failures
```bash
# Check application logs
docker-compose logs flask-app

# Test application health
curl http://localhost:5000/api/students/health

# Check if all dependencies are installed
docker-compose exec flask-app pip list
```

#### 3. Network Connectivity Issues
```bash
# Test service connectivity
docker-compose exec flask-app ping postgres
docker-compose exec nginx ping flask-app

# Check DNS resolution
docker-compose exec flask-app nslookup postgres
```

#### 4. Volume Permission Problems
```bash
# Fix PostgreSQL volume permissions
sudo chown -R 999:999 ./volumes/postgres

# Check volume mounts
docker-compose exec postgres ls -la /var/lib/postgresql/data
```

#### 5. Resource Exhaustion
```bash
# Check container resource usage
docker stats

# Clean up unused resources
make clean

# Increase resource limits in docker-compose.yml
```

#### Diagnostic Commands
```bash
# Comprehensive system check
make status
docker system df
docker network ls
docker volume ls

# Service-specific diagnostics
docker-compose exec postgres pg_isready -U postgres
docker-compose exec flask-app curl -I http://localhost:5000/health

# Log analysis
docker-compose logs --tail=100 flask-app | grep -i error
```

## Production Considerations
### Security Hardening

- Use Secrets Management

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_secret:
    file: ./secrets/api_secret.txt
```

### Network Security

```yaml
networks:
  app-network:
    driver: bridge
    internal: false  # Set to true for internal-only network
```

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Monitoring and Logging
```yaml
# Add logging configuration
services:
  flask-app:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Backup Strategies
```bash
# Database backup script
#!/bin/bash
docker-compose exec postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# Volume backup
docker run --rm -v postgres-data:/source -v $(pwd)/backups:/backup alpine tar czf /backup/postgres_$(date +%Y%m%d).tar.gz -C /source .
```
