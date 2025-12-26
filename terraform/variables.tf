variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "two-az-network"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "azs" {
  type = map(object({
    public        = string
    app           = string
    db            = string
    dependent     = string
    observability = string
  }))
  default = {
    "us-east-1a" = {
      public        = "10.0.0.0/24"
      app           = "10.0.1.0/24"
      db            = "10.0.2.0/24"
      dependent     = "10.0.3.0/24"
      observability = "10.0.4.0/24"
    }
    "us-east-1b" = {
      public        = "10.0.10.0/24"
      app           = "10.0.11.0/24"
      db            = "10.0.12.0/24"
      dependent     = "10.0.13.0/24"
      observability = "10.0.14.0/24"
    }
  }
}

variable "ami_id" {
  default = "ami-020cba7c55df1f615"
}

variable "instance_type" {
  default = "t3.micro"
}

variable "key_name" {
  description = "EC2 key pair name"
}

variable "my_ip" {
  description = "Your public IP for SSH access"

  validation {
    condition     = can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.my_ip))
    error_message = "my_ip must be a valid /32 CIDR, e.g., 203.0.113.25/32"
  }
}
