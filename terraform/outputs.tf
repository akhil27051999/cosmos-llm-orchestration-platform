output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = [for s in aws_subnet.public : s.id]
}

output "app_private_subnet_ids" {
  value = [for s in aws_subnet.app_private : s.id]
}

output "db_private_subnet_ids" {
  value = [for s in aws_subnet.db_private : s.id]
}

output "dependent_private_subnet_ids" {
  value = [for s in aws_subnet.dependent_private : s.id]
}

output "observability_private_subnet_ids" {
  value = [for s in aws_subnet.observability_private : s.id]
}

output "nat_gateway_ids" {
  value = [for ng in aws_nat_gateway.main : ng.id]
}

output "bastion_public_ips" {
  value = [for i in aws_instance.api_server : i.public_ip]
}

output "ssh_commands" {
  value     = [for i in aws_instance.api_server : "ssh -i ${var.key_name}.pem ubuntu@${i.public_ip}"]
  sensitive = true
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_arn" {
  value = aws_lb.main.arn
}

output "target_group_arn" {
  value = aws_lb_target_group.app_tg.arn
}

output "dependent_sg_id" {
  value = aws_security_group.dependent_sg.id
}

output "observability_sg_id" {
  value = aws_security_group.observability_sg.id
}

output "db_sg_id" {
  value = aws_security_group.db_sg.id
}
