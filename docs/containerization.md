# Module 2: Containerization with Docker & Docker Compose

> **Goal:** Package the Flask app as a portable Docker image, then orchestrate the multi-service stack (Flask + Postgres + nginx) with Docker Compose.

> **Why this matters:** Containers are the unit of deployment in modern infrastructure. Every K8s pod runs a container; every CI build produces a container image. If you don't understand Docker layers, networking, and image hygiene, you can't write efficient Dockerfiles, debug pod failures, or pass a DevOps interview.

---

## Table of Contents

1. [Why Containers](#why-containers)
2. [Architecture](#architecture)
3. [Part A — Dockerfile (Single Container)](#part-a--dockerfile-single-container)
4. [Part B — Docker Compose (Multi-Service)](#part-b--docker-compose-multi-service)
5. [Commands Reference](#commands-reference)
6. [Troubleshooting](#troubleshooting)
7. [Interview Q&A](#interview-qa)
8. [STAR Stories](#star-stories)
9. [Production Hardening](#production-hardening)
10. [Cloud Mapping](#cloud-mapping)

---

## Why Containers

| Problem | Container Solution |
|---------|-------------------|
| "Works on my machine" | Image bundles app + deps + runtime — same everywhere |
| Slow VM provisioning (minutes) | Containers start in seconds |
| Inconsistent environments | Image is immutable; run identical in dev/staging/prod |
| Resource waste (one app per VM) | Many containers per host (shared kernel) |
| Hard rollbacks | Pin a previous image tag — instant rollback |

**Container vs VM** — Containers share the host kernel; VMs include a full guest OS. Containers are MB; VMs are GB. Containers start in ms; VMs in minutes.

---

## Architecture

### Single-Container (Dockerfile only)

```
┌────────────────────────────────────────┐
│  Docker Host (your Mac)                │
│  ┌──────────────────────────────────┐  │
│  │  flask-app container (port 8080) │  │
│  │  ┌────────────────────────────┐  │  │
│  │  │ Gunicorn → Flask app       │  │  │
│  │  └────────────────────────────┘  │  │
│  └──────────────────────────────────┘  │
│           ▲                             │
│           │ -p 8080:5000                │
│           │                             │
└───────────┼─────────────────────────────┘
            │
   curl http://localhost:8080
```

### Multi-Service (Docker Compose)

```
┌──────────────────────────────────────────────────────────┐
│  Docker Compose Network: flask-rest-api_default          │
│                                                           │
│  ┌─────────┐    ┌────────────┐    ┌────────────────┐    │
│  │  nginx  │───►│ flask-app  │───►│   postgres     │    │
│  │  :80    │    │   :5000    │    │   :5432        │    │
│  └─────────┘    └────────────┘    └────────────────┘    │
│                                          │               │
│                                          ▼               │
│                                   ┌──────────────┐       │
│                                   │ pgdata volume│       │
│                                   └──────────────┘       │
└──────────────────────────────────────────────────────────┘
       ▲
       │ -p 80:80
   browser → http://localhost
```

---

## Part A — Dockerfile (Single Container)

### Multi-Stage Build Explained

Our Dockerfile uses **two stages** (build + main). This is a common optimization.

**[app/Dockerfile](../app/Dockerfile):**

```dockerfile
# ── Stage 1: build dependencies ────────────────────
FROM python:3.10-alpine AS build
WORKDIR /api/app
RUN apk add --no-cache gcc musl-dev postgresql-dev
COPY requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt \
    && find /root/.local -name '*.pyc' -delete

# ── Stage 2: final image ───────────────────────────
FROM python:3.10-alpine AS main
WORKDIR /api
RUN apk add --no-cache postgresql-client
COPY --from=build /root/.local /root/.local
COPY . ./app
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_APP=app/wsgi.py
EXPOSE 5000
CMD ["gunicorn", "app.wsgi:app"]
```

**Why two stages?**

| Single-stage | Multi-stage |
|--------------|-------------|
| Includes `gcc`, `musl-dev`, build headers in final image | Strips build deps; only runtime libraries remain |
| Image size ~ 400 MB | Image size ~ 80 MB |
| Larger attack surface | Smaller attack surface |

The `build` stage compiles dependencies; the `main` stage **copies only the installed Python packages** from build, then discards everything else. The final image doesn't have `gcc` — smaller, more secure.

### Layer Optimization

Docker caches each `RUN`, `COPY`, `ADD` line as a layer. Cached layers are reused if their inputs don't change.

**Bad pattern** — invalidates cache on every code change:
```dockerfile
COPY . ./app
RUN pip install -r requirements.txt
```

**Good pattern** (what we do) — installs deps before copying source:
```dockerfile
COPY requirements.txt ./
RUN pip install -r requirements.txt   # cached if requirements.txt unchanged
COPY . ./app                          # invalidates only on app code change
```

### Why Alpine?

- Tiny base image (~5 MB vs ~120 MB for `python:3.10-slim`).
- musl libc instead of glibc — smaller, sometimes incompatible with Python wheels.
- Trade-off: slower for some workloads; some packages (e.g., `psycopg2`) need build-from-source.

For production: consider `python:3.10-slim` (Debian-based) — better compatibility, only slightly larger.

### EXPOSE vs Port Mapping

`EXPOSE 5000` is **documentation only** — it doesn't publish the port. It tells Docker (and other developers) which port the app listens on.

To actually publish: `docker run -p 8080:5000` (host:container).

### CMD vs ENTRYPOINT

| Directive | Purpose |
|-----------|---------|
| `CMD` | Default command; **overridable** at runtime |
| `ENTRYPOINT` | Always runs; args appended |

Our `CMD ["gunicorn", "app.wsgi:app"]` is overridable. If you `docker run flask-app:1.0.0 python -c "print('hi')"`, the CMD is replaced.

For wrapper scripts (e.g., a healthcheck loop), use `ENTRYPOINT ["./entrypoint.sh"]` and `CMD ["gunicorn", ...]` — args become positional.

### Build & Run

```bash
cd app
docker build -t flask-app:v1.0.0 .

docker run -d \
  -p 8080:5000 \
  --name student-api \
  --env-file ../.env \
  flask-app:v1.0.0

curl http://localhost:8080/students/3
```

---

## Part B — Docker Compose (Multi-Service)

### Why Compose

Single container is fine for one service. Real apps need DB, cache, reverse proxy, queue. Compose orchestrates **multiple containers** with one YAML file and one command.

### docker-compose.yaml Walkthrough

**[docker-compose.yaml](../docker-compose.yaml):**

```yaml
services:
  flask-app:
    build:
      context: ./app
      dockerfile: Dockerfile
    image: flask-app:1.0.0
    container_name: flask-app-container
    restart: always
    env_file:
      - ${ENV_FILE}
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./:/app

  postgres:
    image: postgres:15
    container_name: postgres-container
    restart: always
    env_file:
      - ${ENV_FILE}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres}"]
      interval: 10s
      timeout: 20s
      retries: 5

  nginx:
    image: nginx:alpine
    container_name: nginx-container
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - flask-app

volumes:
  pgdata:
    driver: local
```

### Key Concepts

| Concept | Explanation |
|---------|-------------|
| **services** | Each is one container (or set of replicas). |
| **build vs image** | `build:` builds locally from a Dockerfile; `image:` tags it. With both, Compose builds AND tags. |
| **restart: always** | Auto-restart on failure or daemon restart. |
| **env_file** | Loads env vars from `.env`. We use `${ENV_FILE}` so the path is parameterized. |
| **depends_on + condition** | Compose starts containers in dependency order. `service_healthy` waits for the healthcheck to pass. |
| **healthcheck** | `pg_isready` runs every 10s. Until it passes 5 times, the service is "unhealthy" and dependents wait. |
| **ports** | `host:container`. Postgres exposed for local debugging only — in K8s we'd keep it ClusterIP. |
| **volumes** | Two kinds: bind mount (`./:/app`) and named volume (`pgdata:/var/lib/postgresql/data`). |
| **networks** | Compose auto-creates a default network. All services can reach each other by service name (`postgres`, `flask-app`). |

### Networking — Service Discovery via DNS

Inside the Compose network, services resolve each other by name:
- `flask-app` connects to Postgres at `postgres:5432`
- `nginx` proxies to `flask-app:5000`

This is what's set in [nginx/nginx.conf](../nginx/nginx.conf):
```nginx
upstream flask_backend {
    server flask-app:5000;
}
```

Same DNS pattern carries into Kubernetes — services resolve via cluster DNS.

### Volumes — Bind Mounts vs Named Volumes

| Bind Mount (`./:/app`) | Named Volume (`pgdata:/...`) |
|------------------------|------------------------------|
| Maps a host path into the container | Docker manages storage location |
| Useful for live code reload during dev | Useful for persistent DB data |
| Easy to inspect on host | Survives container deletion |
| Subject to host filesystem perms | Portable across hosts |

### Run

```bash
export ENV_FILE=.env          # docker-compose.yaml uses this
docker compose up -d --build  # build & start in background
docker compose ps             # check status
docker compose logs -f nginx  # tail logs
```

Test via nginx: `curl http://localhost/students/3`.

### Database Bootstrap

Postgres starts empty. After `docker compose up`:

```bash
# Apply Flask migrations
docker exec flask-app-container flask db upgrade --directory app/migrations

# Seed data
docker exec -e PYTHONPATH=/api flask-app-container python /api/app/seed.py
```

---

## Commands Reference

### Docker (Single Container)

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Build image | `docker build -t flask-app:v1.0.0 .` | Creates image from Dockerfile |
| 2 | Run container | `docker run -d -p 8080:5000 --name app --env-file ../.env flask-app:v1.0.0` | Detached, mapped port, env vars |
| 3 | List running | `docker ps` | See active containers |
| 4 | List all (incl. stopped) | `docker ps -a` | Shows exited containers |
| 5 | Logs | `docker logs -f app` | Stream logs |
| 6 | Exec into container | `docker exec -it app sh` | Shell inside running container |
| 7 | Stop | `docker stop app` | Graceful SIGTERM |
| 8 | Remove | `docker rm app` | Delete stopped container |
| 9 | Force remove | `docker rm -f app` | Stop + remove |
| 10 | Image list | `docker images` | Show all images |
| 11 | Remove image | `docker rmi flask-app:v1.0.0` | Delete image |
| 12 | Inspect | `docker inspect app` | All container metadata as JSON |
| 13 | Stats | `docker stats` | Live CPU/mem/IO per container |
| 14 | Prune | `docker system prune -a --volumes` | Reclaim disk space |

### Docker Compose

| Sl. No | Description | Command | Why |
|--------|-------------|---------|-----|
| 1 | Set env file var | `export ENV_FILE=.env` | Compose YAML references it |
| 2 | Build & start | `docker compose up -d --build` | Detached, force rebuild |
| 3 | Stop & remove | `docker compose down` | Stop containers + remove network |
| 4 | Stop + remove volumes | `docker compose down -v` | Wipes DB data — destructive! |
| 5 | Status | `docker compose ps` | Show service states |
| 6 | Logs (one) | `docker compose logs -f flask-app` | Stream a service's logs |
| 7 | Logs (all) | `docker compose logs -f` | Tail all services |
| 8 | Restart one | `docker compose restart flask-app` | Useful after config change |
| 9 | Run one-off | `docker compose run --rm flask-app pytest` | Run command in new container |
| 10 | Exec | `docker compose exec flask-app sh` | Shell in running service |

---

## Troubleshooting

| Sl. No | Issue | Cause | Fix |
|--------|-------|-------|-----|
| 1 | `docker: command not found` | Docker Desktop not installed / not in PATH | Install Docker Desktop, restart shell |
| 2 | Intel Docker on Apple Silicon | Wrong architecture | Reinstall ARM64 build from docker.com |
| 3 | `port is already allocated: 0.0.0.0:5000` | macOS AirPlay holds 5000 | Map to different host port: `-p 8080:5000` |
| 4 | `Connection reset by peer` from `curl localhost:8080` | Gunicorn binds to `127.0.0.1:8000` (loopback) by default; unreachable outside container | Add `GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000 --workers=2` to env, OR `CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.wsgi:app"]` |
| 5 | App container can't reach Postgres at `localhost` | Inside container, `localhost` = the container itself, not host | Use `host.docker.internal` (single container) or service name `postgres` (compose/K8s) |
| 6 | `env file not found: stat : no such file` | `${ENV_FILE}` was not exported | `export ENV_FILE=.env` first |
| 7 | `flask db upgrade: Path doesn't exist: migrations` | Working dir is `/api`, migrations at `/api/app/migrations` | `flask db upgrade --directory app/migrations` |
| 8 | `python: can't open file '/api/app/seed.py'` | seed.py wasn't copied (was at project root, Dockerfile copies only `./app`) | Move `seed.py` into `app/` folder so it's bundled in the image |
| 9 | `ModuleNotFoundError: No module named 'app'` when running seed.py | PYTHONPATH doesn't include `/api` | `docker exec -e PYTHONPATH=/api flask-app-container python /api/app/seed.py` |
| 10 | Container exits immediately | CMD finished (e.g., a shell command, not a long-running server) | Ensure CMD runs a foreground process. Check `docker logs <container>` |
| 11 | Pulled `flask-app:v1.0.0` from registry but it 's local-only | Without registry prefix, Docker tries pulling from Docker Hub | Build locally first OR push to registry |
| 12 | `unhealthy` postgres in compose | Healthcheck failing — wrong creds or port | `docker compose logs postgres`; verify env vars; check timing/retries |
| 13 | Disk full | Old images and volumes accumulate | `docker system prune -a --volumes` |
| 14 | Image build is slow on every code change | `COPY . .` invalidates cache | Copy `requirements.txt` and install deps BEFORE copying source |

---

## Interview Q&A

| Q | A |
|---|---|
| **Container vs VM?** | Containers share the host kernel; lightweight (~MB), fast startup (ms). VMs include a full guest OS; heavier (~GB), slower (minutes). Containers run on top of VMs in cloud environments. |
| **Why multi-stage builds?** | Smaller image size (build deps stripped), smaller attack surface, faster pulls. Final image only has runtime, not compilers. |
| **Difference between CMD and ENTRYPOINT?** | CMD = default command, overridable. ENTRYPOINT = always runs, args appended. Combine them: ENTRYPOINT `["python"]`, CMD `["app.py"]`. Override CMD: `docker run img script.py`. |
| **Difference between EXPOSE and -p?** | EXPOSE is documentation only — declares which port the container uses. `-p host:container` actually publishes it on the host. |
| **What's a Docker layer?** | Each `RUN`, `COPY`, `ADD` creates a layer (read-only filesystem diff). Layers are cached and shared between images. |
| **Why does layer order matter?** | Cached layers are reused if their inputs haven't changed. Put rarely-changing things (deps install) before frequently-changing things (source copy) for build speed. |
| **What's a bind mount vs volume?** | Bind mount = host path mapped into container (`./code:/app`). Volume = Docker-managed storage (`pgdata:/var/lib/postgresql/data`). Volumes survive container deletion; bind mounts depend on host. |
| **How does container networking work?** | Each Docker network gets its own bridge. Containers on the same network resolve each other by name (DNS). Use `docker network ls` to inspect. |
| **What's `host.docker.internal`?** | Mac/Windows-only DNS name that resolves to the host machine from inside a container. On Linux, use `--add-host=host.docker.internal:host-gateway`. |
| **`docker run` vs `docker exec`?** | `run` starts a new container. `exec` runs a command inside an existing one. |
| **What's a healthcheck?** | Periodic command Docker runs to determine container health. Failing healthchecks mark container as `unhealthy` (visible in `docker ps`); compose `depends_on: condition: service_healthy` waits for it. |
| **`docker compose down` vs `docker compose down -v`?** | `down` removes containers + network. `-v` also deletes named volumes (and your data). |
| **How do you reduce image size?** | Multi-stage builds, slim/alpine base, `--no-install-recommends` (apt), cleanup in same RUN, `.dockerignore`, distroless images. |
| **What's `.dockerignore`?** | Like `.gitignore` but for Docker. Excludes files from build context (e.g., `.git`, `node_modules`, `.env`). Smaller context = faster builds, smaller images. |
| **How do you scan images for vulnerabilities?** | `docker scout` (built-in), Trivy, Snyk, Grype. Run in CI on every build; block on critical CVEs. |
| **Difference between `docker compose` and `docker-compose`?** | `docker-compose` = old standalone Python tool (v1). `docker compose` = new built-in Go subcommand (v2). Same YAML format. |
| **How does `depends_on` work?** | Compose starts services in dependency order, but `depends_on: postgres` only waits for postgres to **start**, not to be **ready**. Add `condition: service_healthy` to wait for healthcheck. |
| **What's the difference between `--rm` and `-d`?** | `--rm` removes container on exit (good for one-shot commands). `-d` runs detached (background). |
| **What runs as PID 1 in a container?** | Whatever your CMD/ENTRYPOINT is. PID 1 has special signal handling — if it doesn't handle SIGTERM, `docker stop` will SIGKILL after timeout. Use `tini` or proper signal handling. |
| **What's a distroless image?** | An image with no shell, package manager, or extras — only your app + minimal runtime. Maximum security. Pioneered by Google. |

---

## STAR Stories

### Story 1: "Tell me about a time you debugged a network issue inside a container."

**Situation:** After dockerizing the Flask app, every `curl http://localhost:8080/students/3` returned `Connection reset by peer`. Container was running, logs showed Gunicorn started successfully.

**Task:** Figure out why the container was unreachable despite running.

**Action:**
1. Ran `docker logs flask-app` — Gunicorn was listening on `127.0.0.1:8000`.
2. Realized Gunicorn defaults to **loopback only** — meaning the address is reachable only from inside the container itself, not from the host or other containers.
3. Two issues: wrong port (8000 vs our EXPOSE 5000) AND wrong bind address (loopback).
4. Fixed via env var: `GUNICORN_CMD_ARGS=--bind=0.0.0.0:5000 --workers=2`.
5. `0.0.0.0` binds to all interfaces, making the port reachable through the Docker port mapping.

**Result:** Container responding within 5 minutes of fix. Wrote a quick reference: "App must bind to 0.0.0.0 — never 127.0.0.1 — to be reachable through Docker port mapping."

**Takeaway:** Same lesson scales up — in K8s, the pod's app must bind to 0.0.0.0 for the Service to route traffic to it. Loopback binding is a top-3 cause of "container running but unreachable."

---

### Story 2: "Tell me about a time you optimized a Docker image."

**Situation:** Initial Flask Docker image was ~400 MB — slow to push, slow to pull, large attack surface.

**Task:** Reduce image size without breaking functionality.

**Action:**
1. Switched base from `python:3.10` (Debian, ~120 MB) to `python:3.10-alpine` (~50 MB).
2. Identified `gcc` and `postgresql-dev` as build-only deps for compiling psycopg2.
3. Refactored to multi-stage build: stage 1 has compilers, stage 2 only the compiled `.local` directory.
4. Reordered Dockerfile: copy requirements.txt first, install, then copy source — so dep install layer is cached unless requirements change.
5. Added `.dockerignore` to exclude `venv/`, `.git/`, `__pycache__/`.

**Result:** Final image ~80 MB (5x reduction). Build time after first build: ~10 sec instead of ~90 sec (cached deps layer). CI minutes saved across the team.

**Takeaway:** Multi-stage + alpine + layer ordering + .dockerignore = standard playbook for image hygiene. Always justify each layer in your Dockerfile.

---

### Story 3: "Tell me about a time you had a port conflict in production."

**Situation:** Trying to bind a Flask container to port 5000 on a macOS dev machine — Docker error: `bind: address already in use`.

**Task:** Identify what was holding the port and unblock the dev workflow.

**Action:**
1. `lsof -i :5000` revealed `ControlCenter` (macOS AirPlay Receiver) and previously-killed Flask processes.
2. Killed the Flask processes; ControlCenter was a system process — couldn't easily kill.
3. Two options: disable AirPlay in System Settings (intrusive) or remap the host port.
4. Chose `-p 8080:5000` so Docker maps host 8080 → container 5000. Same app, different external port.
5. Documented this in our team's setup guide for macOS users.

**Result:** Unblocked dev work without disabling system features. Avoided the same issue for new joiners.

**Takeaway:** Port conflicts are about the host, not the container. Always use port mapping flexibly; the container's internal port can stay 5000 (matching EXPOSE) while the host exposes whatever's free.

---

## Production Hardening

| Area | Current | Production |
|------|---------|-----------|
| **Base image** | `python:3.10-alpine` | `python:3.10-slim` (better compatibility) or distroless (max security) |
| **User** | Root | Non-root: `RUN adduser -D appuser && USER appuser` |
| **Image scanning** | None | Trivy / Snyk in CI; block on critical CVEs |
| **Image signing** | None | Cosign / Notary; verify in admission controller |
| **Secrets in env vars** | OK for dev | Mount as files via secret manager (Vault, K8s Secrets); env vars can leak via crash dumps |
| **Healthcheck** | None in Dockerfile | Add `HEALTHCHECK CMD curl -f http://localhost:5000/health \|\| exit 1` |
| **Logging** | stdout (default) | Structured JSON; ship via fluent-bit/Promtail |
| **Resource limits** | None | `--memory=512m --cpus=0.5` (Docker run); requests/limits in K8s |
| **Read-only root FS** | Read-write | `--read-only --tmpfs /tmp` for stateless apps |
| **Image registry** | Local | Private registry (ECR, GCR, GHCR); pull secrets configured |
| **Image tag** | `v1.0.0` static | SHA-based tags (immutable); plus semver tags for human reference |
| **Build cache** | Local | BuildKit + remote cache (e.g., GHA cache) for fast CI builds |
| **SBOM** | None | Generate Software Bill of Materials with Syft; track for compliance |

---

## Cloud Mapping

| Local | AWS | GCP | Azure |
|-------|-----|-----|-------|
| `docker run` | ECS / Fargate / EC2 | Cloud Run / GCE | ACI / AKS |
| `docker push` (registry) | ECR | Artifact Registry | ACR |
| Docker Compose (multi-service) | ECS Service definitions / EKS | GKE | AKS |
| `docker network` | VPC subnet | VPC | VNet |
| `docker volume` | EBS / EFS | Persistent Disk | Azure Disks |
| `restart: always` | ECS task scheduler / K8s Deployment | Cloud Run autoscaler | AKS |
| Healthcheck | ELB target group health check | Cloud Load Balancer | App Gateway |

---

## Reference Links (Internal)

- App Dockerfile: [app/Dockerfile](../app/Dockerfile)
- nginx Dockerfile: [nginx/Dockerfile](../nginx/Dockerfile)
- nginx config: [nginx/nginx.conf](../nginx/nginx.conf)
- docker-compose: [docker-compose.yaml](../docker-compose.yaml)
- Env file template: [.env](../.env) (gitignored)
