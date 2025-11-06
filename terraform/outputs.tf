output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.api_server.public_ip
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.api_server.id
}

output "ssh_connection_command" {
  description = "SSH connection command"
  value       = "ssh -i ${var.key_name}.pem ubuntu@${aws_eip.api_server.public_ip}"
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

# Remove the problematic next_steps output or fix it:
output "next_steps" {
  description = "Next steps after deployment"
  value       = <<EOT
Next steps:
1. SSH to the instance: ssh -i ${var.key_name}.pem ubuntu@${aws_eip.api_server.public_ip}
2. The instance is ready for Ansible configuration
EOT
}