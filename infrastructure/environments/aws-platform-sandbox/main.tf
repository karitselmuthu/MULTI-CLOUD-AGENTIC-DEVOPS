provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]
  default_tags {
    tags = {
      owner       = var.owner
      cost_center = var.cost_center
      environment = "sandbox"
    }
  }
}

data "aws_subnet" "alb" {
  for_each = toset(var.alb_subnet_ids)
  id       = each.value
}

data "aws_subnet" "task" {
  for_each = toset(var.task_subnet_ids)
  id       = each.value
}

locals {
  secret_arns = [
    var.database_url_secret_arn,
    var.temporal_api_key_secret_arn,
    var.signing_key_secret_arn,
    var.dashboard_token_secret_arn,
  ]
  common_environment = [
    { name = "AWS_SANDBOX_MODE", value = "1" },
    { name = "LOCAL_MOCK_APPROVAL_ENABLED", value = "0" },
    { name = "LOCAL_DASHBOARD_REQUESTER", value = var.dashboard_requester },
    { name = "TEMPORAL_ADDRESS", value = var.temporal_address },
    { name = "TEMPORAL_NAMESPACE", value = var.temporal_namespace },
    { name = "OPA_BIN", value = "/usr/local/bin/opa" },
  ]
  common_secrets = [
    { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
    { name = "TEMPORAL_API_KEY", valueFrom = var.temporal_api_key_secret_arn },
    { name = "AGENT_SIGNING_KEY", valueFrom = var.signing_key_secret_arn },
    { name = "LOCAL_DASHBOARD_TOKEN", valueFrom = var.dashboard_token_secret_arn },
  ]
  common_log_options = {
    awslogs-group         = aws_cloudwatch_log_group.platform.name
    awslogs-region        = var.aws_region
    awslogs-stream-prefix = "ecs"
  }
}

resource "aws_cloudwatch_log_group" "platform" {
  name              = "/ecs/${var.name}"
  retention_in_days = 14
}

resource "aws_ecs_cluster" "platform" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role" "api" {
  name               = "${var.name}-api"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role" "worker" {
  name               = "${var.name}-worker"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "execution" {
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    actions   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
    resources = [var.ecr_repository_arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.platform.arn}:*"]
  }
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = local.secret_arns
  }
}

resource "aws_iam_role_policy" "execution" {
  name   = "${var.name}-execution"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "tasks" {
  name_prefix = "${var.name}-tasks-"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  for_each          = toset(var.allowed_ingress_cidrs)
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.tasks.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id            = aws_security_group.tasks.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "task_egress" {
  security_group_id = aws_security_group.tasks.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_lb" "api" {
  name               = var.name
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.alb_subnet_ids
  lifecycle {
    precondition {
      condition     = length(distinct([for subnet in data.aws_subnet.alb : subnet.availability_zone])) >= 2
      error_message = "ALB subnets must span at least two Availability Zones."
    }
    precondition {
      condition = alltrue([
        for subnet in data.aws_subnet.alb :
        subnet.vpc_id == var.vpc_id && !subnet.map_public_ip_on_launch
      ])
      error_message = "ALB subnets must belong to the selected VPC and disable public IP assignment."
    }
  }
}

resource "aws_lb_target_group" "api" {
  name        = var.name
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.tls_certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  container_definitions = jsonencode([{
    name                   = "api"
    image                  = var.image_uri
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
    environment            = local.common_environment
    secrets                = local.common_secrets
    stopTimeout            = 60
    logConfiguration       = { logDriver = "awslogs", options = local.common_log_options }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.worker.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  container_definitions = jsonencode([{
    name                   = "worker"
    image                  = var.image_uri
    essential              = true
    readonlyRootFilesystem = true
    command                = ["python", "-m", "orchestration.temporal.workers.mock_worker"]
    environment            = local.common_environment
    secrets                = local.common_secrets
    stopTimeout            = 60
    logConfiguration       = { logDriver = "awslogs", options = local.common_log_options }
  }])
}

resource "aws_ecs_task_definition" "migration" {
  family                   = "${var.name}-migration"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.api.arn
  container_definitions = jsonencode([{
    name                   = "migration"
    image                  = var.image_uri
    essential              = true
    readonlyRootFilesystem = true
    command                = ["python", "-m", "apps.api.init_db"]
    secrets                = [{ name = "DATABASE_URL", valueFrom = var.database_url_secret_arn }]
    logConfiguration       = { logDriver = "awslogs", options = local.common_log_options }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.name}-api"
  cluster         = aws_ecs_cluster.platform.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.task_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  depends_on = [
    aws_lb_listener.https,
    aws_vpc_security_group_ingress_rule.api_from_alb,
    aws_vpc_security_group_egress_rule.alb_to_api,
  ]
  lifecycle {
    precondition {
      condition = alltrue([
        for subnet in data.aws_subnet.task :
        subnet.vpc_id == var.vpc_id && !subnet.map_public_ip_on_launch
      ])
      error_message = "Task subnets must belong to the selected VPC and disable public IP assignment."
    }
  }
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker"
  cluster         = aws_ecs_cluster.platform.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.task_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
