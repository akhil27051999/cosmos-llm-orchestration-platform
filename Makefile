# Makefile for Flask REST API 

# Local Variables
PYTHON = python
PIP = pip
PYTEST = pytest
FLASK_APP = app
REQ = requirements.txt

# Docker Variables
DOCKER_IMAGE = flask-app
DOCKER_IMAGE_TAG ?= 1.0.0
DOCKER_HUB_USERNAME = akhilthyadi

# Docker Compose Services
FLASK_APP_1 = flask-app-1
FLASK_APP_2 = flask-app-2
DB_SERVICE = postgres
NGINX_SERVICE = nginx

# Default Goal
.DEFAULT_GOAL := help

# Help
help:
	@echo "Available commands:"
	@echo "  Local:"
	@echo "    make install        Install dependencies from requirements.txt"
	@echo "    make freeze         Freeze dependencies to requirements.txt"
	@echo "    make lint           Run linting on Python code"
	@echo "    make run            Run Flask app locally"
	@echo "    make test           Run unit tests with pytest"
	@echo "    make clean          Remove Python cache and pytest cache"
	@echo ""
	@echo "  Docker (single container):"
	@echo "    make docker-build   Build single Flask Docker image"
	@echo "    make docker-run     Run single Flask Docker container"
	@echo "    make docker-stop    Stop and remove single container"
	@echo "    make docker-logs    View logs of single container"
	@echo "    make docker-clean   Remove Docker image"
	@echo "    make docker-push    Push Docker image to Docker Hub"
	@echo ""
	@echo "  Docker Compose (multi-service):"
	@echo "    make compose-build  Build all Docker Compose services"
	@echo "    make compose-up     Start all services (DB + API + Nginx)"
	@echo "    make compose-down   Stop all services and remove volumes"
	@echo "    make compose-logs   View logs of all services"
	@echo "    make db             Start only the Postgres DB service"
	@echo "    make migrate        Run DB migrations on $(FLASK_APP_1)"
	@echo "    make seed           Seed dummy data into DB via $(FLASK_APP_1)"

# Local commands

install:
	$(PIP) install -r $(REQ)

freeze:
	$(PIP) freeze > $(REQ)

lint:
	pylint app tests || true

run:
	FLASK_APP=$(FLASK_APP) flask run --host=0.0.0.0 --port=5000

test:
	$(PYTEST) -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache


# Docker commands

docker-build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG) -f app/Dockerfile ./app

docker-run:
	docker run -d -p 5000:5000 --name $(DOCKER_IMAGE) $(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG)

docker-stop:
	docker stop $(DOCKER_IMAGE) || true
	docker rm $(DOCKER_IMAGE) || true

docker-logs:
	docker logs -f $(DOCKER_IMAGE)

docker-clean:
	docker rmi $(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG) || true

docker-push:
	docker tag $(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG) $(DOCKER_HUB_USERNAME)/$(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG)
	docker push $(DOCKER_HUB_USERNAME)/$(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG)


# Docker Compose commands (multi-service)

compose-build:
	docker compose build

compose-up:
	docker compose up -d

compose-down:
	docker compose down -v

compose-logs:
	docker compose logs -f

db:
	docker compose up -d $(DB_SERVICE)

migrate:
	docker compose exec $(FLASK_APP_1) flask db upgrade

seed:
	docker compose exec -w /app $(FLASK_APP_1) python seed.py

# Phony targets
.PHONY: help install freeze lint run test clean \
        docker-build docker-run docker-stop docker-logs docker-clean docker-push \
        compose-build compose-up compose-down compose-logs db migrate seed
