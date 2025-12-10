# REST-API-CI-Pipeline Documentation

<img width="688" height="310" alt="Screenshot 2025-12-10 195544" src="https://github.com/user-attachments/assets/017af6e0-6c27-4bc4-b7c4-67b6aa070a25" />

### Overview
This GitHub Actions workflow implements a comprehensive CI/CD pipeline for a REST API application. The pipeline automates building, testing, linting, containerization, and deployment of a Flask application using Docker and Helm.

## Milestone Expectations

### Problem Statement
- We want to create a simple CI pipeline that will be used to build and push our docker image to a central registry. You can use DockerHub or GitHub docker registry as a central docker registry.

### Expectations

The following expectations should be met to complete this milestone.
- CI pipeline should consist of the following stages
  - Build API
  - Run tests
  - Perform code linting
  - Docker login
  - Docker build and push
- To achieve the stages of building, testing, and performing code linting, you need to use appropriate make targets.
- CI pipeline should be run using a self-hosted GitHub runner running on your local machine.
- CI pipeline should only be triggered when changes are made in the code directory and not in other directories or filepaths.
- CI workflow should allow the developer to manually trigger the pipeline when required.

## Pipeline Triggers
### Automatic Triggers
- Push events to dev or main branches
- Pull requests targeting dev or main branches
- Path filtering: Only triggers when changes occur in the app/ directory

### Manual Trigger
- Workflow Dispatch: Allows manual execution via GitHub UI when needed

## Jobs and Stages

### Job 1: Build
- Runner: Self-hosted GitHub runner

**Steps:**

#### 1. Checkout Code
- Uses actions/checkout@v3 to fetch repository code

#### 2. Python Environment Setup

- Configures Python 3.12 using actions/setup-python@v4
- Installs project dependencies from app/requirements.txt

#### 3. Testing
- Executes pytest test suite with SQLite database
- Provides verbose output for test results

#### 4. Docker Image Build
- Builds Docker image with tag based on Git SHA (first 7 characters)
- Stores image tag as output for subsequent jobs

#### 5. Docker Registry Login
- Authenticates to Docker Hub using secrets:
  - DOCKER_HUB_USERNAME
  - DOCKER_HUB_ACCESS_TOKEN

#### 6. Image Push
- Tags image with Docker Hub repository format
- Pushes image to Docker Hub registry

#### 7. Cleanup
- Removes local Docker images to free up disk space

### Job 2: Update Helm Charts
- Dependency: Requires successful completion of Build job
- Runner: Self-hosted GitHub runner

**Steps:**

#### 1. Repository Checkout
- Fetches latest code including Helm charts

#### 2. Git Configuration
- Sets up commit author information

#### 3. Branch Synchronization
- Ensures main branch is up to date

#### 4. Helm Chart Update
- Uses sed to update image tag in values.yaml
- Updates the application version with the newly built Docker image

#### 5. Commit and Push
- Commits the Helm chart changes
- Pushes updates back to repository using GitHub token

## Configuration Requirements
### Secrets
- The following secrets must be configured in your GitHub repository:
  - DOCKER_HUB_USERNAME: Docker Hub username
  - DOCKER_HUB_ACCESS_TOKEN: Docker Hub access token
  - GITHUB_TOKEN: Automatically provided by GitHub

## Key Features
### Conditional Execution
- Only runs when app/ directory changes
- Prevents unnecessary pipeline executions

### Manual Control
- Supports on-demand execution via GitHub Actions UI

### Self-Hosted Runners
- Utilizes your own infrastructure for execution
- Provides control over build environment

### Artifact Management
- Automatically tags Docker images with Git commit references
- Updates Helm charts with new image versions

### Cleanup
- Removes temporary Docker images to maintain runner performance

## Usage
### Automatic Execution
- Push code to app/ directory in dev/main branches
- Create pull requests modifying app/ directory

### Manual Execution
1. Navigate to GitHub Actions tab
2. Select "REST-API-CI-Pipeline"
3. Click "Run workflow"
4. Choose branch and click "Run workflow"

#### Output
- Docker image pushed to: {DOCKER_HUB_USERNAME}/flask-app:{git_sha}
- Updated Helm chart in repository
- Test results and build logs in GitHub Actions interface

> This pipeline ensures consistent, automated deployment of your REST API with proper testing and version management through containerization and infrastructure-as-code practices.
