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

    # Add Docker's official GPG key
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

install_terraform() {
    log "Installing Terraform..."
    
    # Install prerequisites
    sudo apt-get install -y gnupg software-properties-common curl
    
    # Add HashiCorp GPG key
    wget -O- https://apt.releases.hashicorp.com/gpg | \
    sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    
    # Add HashiCorp repository
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
    https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/hashicorp.list
    
    # Install Terraform
    sudo apt-get update -y
    sudo apt-get install -y terraform
    
    # Verify installation
    terraform --version
}

install_ansible() {
    log "Installing Ansible..."
    
    # Update package index and install dependencies
    sudo apt-get update -y
    sudo apt-get install -y python3-pip
    
    # Install Ansible via pip (more up-to-date version)
    pip3 install --user ansible
    
    # Add user bin directory to PATH if not already there
    if ! grep -q ".local/bin" ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
    export PATH="$HOME/.local/bin:$PATH"
    
    # Install common Ansible collections
    ansible-galaxy collection install community.general
    
    # Verify installation
    ansible --version
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

    # Install kind
    curl -Lo ./kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
    chmod +x ./kind
    sudo mv ./kind /usr/local/bin/kind
}

install_helm() {
    log "Installing Helm..."
    
    # Download and install Helm
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
    chmod 700 get_helm.sh
    ./get_helm.sh
    rm get_helm.sh
    
    # Add Helm repository
    helm repo add stable https://charts.helm.sh/stable
    helm repo update
    
    # Verify installation
    helm version
}

main() {
    update_system
    install_basic_tools
    install_postgres_client
    install_docker
    install_terraform
    install_ansible
    install_kubernetes_tools
    install_helm

    log "Bootstrap completed!"
    log "Please log out and log back in (or run 'newgrp docker') to use Docker without sudo."
    log "Run 'minikube start --driver=docker --nodes 3' to start your Kubernetes cluster."
    log "After that, you can label nodes with:"
    echo "kubectl label node minikube type=application"
    echo "kubectl label node minikube-m02 type=database"
    echo "kubectl label node minikube-m03 type=dependent_services"
    log "Terraform, Ansible, and Helm are now available for infrastructure automation and package management."
}

main "$@"