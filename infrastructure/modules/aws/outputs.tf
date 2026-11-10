output "network_id" {
  description = "Sandbox VPC identifier."
  value       = aws_vpc.sandbox.id
}

output "private_subnet_id" {
  description = "Private subnet identifier."
  value       = aws_subnet.private.id
}

output "registry_url" {
  description = "Private image repository URL."
  value       = aws_ecr_repository.images.repository_url
}
