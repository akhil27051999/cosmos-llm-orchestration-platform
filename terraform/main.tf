terraform {
  required_version = ">=1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

############################
# VPC
############################
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

############################
# Internet Gateway
############################
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

############################
# Subnets
############################
resource "aws_subnet" "public" {
  for_each = var.azs
  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.public
  availability_zone       = each.key
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${each.key}"
  }
}

resource "aws_subnet" "app_private" {
  for_each = var.azs
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.app
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-app-private-${each.key}"
  }
}

resource "aws_subnet" "db_private" {
  for_each = var.azs
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.db
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-db-private-${each.key}"
  }
}

resource "aws_subnet" "dependent_private" {
  for_each = var.azs
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.dependent
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-dependent-private-${each.key}"
  }
}

resource "aws_subnet" "observability_private" {
  for_each = var.azs
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.observability
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-observability-private-${each.key}"
  }
}

############################
# NAT Gateways
############################
resource "aws_eip" "nat" {
  for_each = var.azs
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip-${each.key}"
  }
}

resource "aws_nat_gateway" "main" {
  for_each      = var.azs
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = {
    Name = "${var.project_name}-nat-gw-${each.key}"
  }

  depends_on = [aws_internet_gateway.main]
}

############################
# Route Tables
############################
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  for_each      = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  for_each = var.azs
  vpc_id   = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[each.key].id
  }

  tags = { Name = "${var.project_name}-private-rt-${each.key}" }
}

resource "aws_route_table_association" "app_private" {
  for_each      = aws_subnet.app_private
  subnet_id     = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_route_table_association" "dependent_private" {
  for_each      = aws_subnet.dependent_private
  subnet_id     = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_route_table_association" "observability_private" {
  for_each      = aws_subnet.observability_private
  subnet_id     = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

resource "aws_route_table" "private_db" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-private-db-rt" }
}

resource "aws_route_table_association" "db_private" {
  for_each      = aws_subnet.db_private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_db.id
}

############################
# Security Groups
############################
# ALB SG
resource "aws_security_group" "alb_sg" {
  name   = "${var.project_name}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-alb-sg" }
}

# App SG
resource "aws_security_group" "app_sg" {
  name   = "${var.project_name}-app-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description      = "Allow HTTP from ALB"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    security_groups  = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-app-sg" }
}

# Bastion/Test SG
resource "aws_security_group" "api_server" {
  name   = "${var.project_name}-bastion-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-bastion-sg" }
}

# Dependent SG
resource "aws_security_group" "dependent_sg" {
  name   = "${var.project_name}-dependent-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Observability SG
resource "aws_security_group" "observability_sg" {
  name   = "${var.project_name}-observability-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    security_groups = [aws_security_group.app_sg.id, aws_security_group.dependent_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# DB SG
resource "aws_security_group" "db_sg" {
  name   = "${var.project_name}-db-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

############################
# EC2 Instances
############################
resource "aws_instance" "api_server" {
  for_each = aws_subnet.public
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = each.value.id
  vpc_security_group_ids      = [aws_security_group.api_server.id]
  key_name                    = var.key_name
  associate_public_ip_address = true

  tags = { Name = "${var.project_name}-bastion-${each.key}" }
}

############################
# ALB
############################
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [for s in aws_subnet.public : s.id]

  enable_deletion_protection = false
  idle_timeout               = 60

  tags = { Name = "${var.project_name}-alb" }
}

resource "aws_lb_target_group" "app_tg" {
  name        = "${var.project_name}-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"

  health_check {
    interval            = 30
    path                = "/"
    port                = "80"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
  }

  tags = { Name = "${var.project_name}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
  }
}

resource "aws_lb_target_group_attachment" "app_instances" {
  for_each = aws_instance.api_server
  target_group_arn = aws_lb_target_group.app_tg.arn
  target_id        = each.value.id
  port             = 80
}
