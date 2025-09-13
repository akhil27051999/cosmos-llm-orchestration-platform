#!/usr/bin/env bash

set -e  # exit on error
set -u  # treat unset vars as errors
set -o pipefail # catch errors in pipelines

GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[+] $1${NC}"
}

update_system() {
    log "Updating system packages..."
    sudo apt-get update -y
    sudo apt-get upgrade -y
}

install_basic_tools() {
    log "Installing basic tools (curl, wget, unzip, git, make, python3, pip, venv)..."
    sudo apt-get install -y \
        curl wget unzip git make \
        python3 python3-pip python3-venv \
        software-properties-common apt-transport-https ca-certificates gnupg lsb-release
}

install_postgres_client() {
    log "Installing PostgreSQL client..."
    sudo apt-get install -y postgresql-client
}

install_docker() {
    log "Installing Docker CE..."
    sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

    # Add Docker’s official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg

    # Set up stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo systemctl enable docker
    sudo usermod -aG docker vagrant || true
}

install_kubernetes_tools() {
    log "Installing Kubernetes tools (kubectl, minikube)..."

    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    chmod +x kubectl
    sudo mv kubectl /usr/local/bin/

    # Install minikube
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube
    rm -f minikube-linux-amd64
}

install_kubernetes_tools() {
    log "Installing Kubernetes tools (kubectl, minikube, kind)..."
    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl

    # Install minikube
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    sudo install minikube-linux-amd64 /usr/local/bin/minikube
    rm minikube-linux-amd64

}

main() {
    update_system
    install_basic_tools
    install_postgres_client
    install_docker
    install_kubernetes_tools

    log "Bootstrap completed!"
    log "Please log out and log back in (or run 'newgrp docker') to use Docker without sudo."
    log "Run 'minikube start --driver=docker --nodes 3' to start your Kubernetes cluster."
    log "After that, you can label nodes with:"
    echo "kubectl label node minikube type=application"
    echo "kubectl label node minikube-m02 type=database"
    echo "kubectl label node minikube-m03 type=dependent_services"
}

main "$@"
