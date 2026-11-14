output "cluster_arn" {
  value = aws_ecs_cluster.platform.arn
}

output "migration_task_definition_arn" {
  value = aws_ecs_task_definition.migration.arn
}

output "task_security_group_id" {
  value = aws_security_group.tasks.id
}

output "internal_alb_dns_name" {
  value = aws_lb.api.dns_name
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "worker_service_name" {
  value = aws_ecs_service.worker.name
}
