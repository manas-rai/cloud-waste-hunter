# ECS Cluster
resource "aws_ecs_cluster" "this" {
  name = "cluster-${var.environment}"
  tags = var.tags
}

# ALB
resource "aws_lb" "this" {
  name               = "alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
  tags               = var.tags
}

resource "aws_security_group" "alb" {
  name   = "alb-sg-${var.environment}"
  vpc_id = var.vpc_id
  tags   = var.tags

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "tg-backend-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check {
    path = "/health"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = "80"
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "backend-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.app_role_arn
  task_role_arn            = var.app_role_arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = var.backend_image
      essential = true
      portMappings = [{ containerPort = 8000, hostPort = 8000 }]
      environment = [{ name = "DATABASE_URL", value = var.db_url }]
    }
  ])
}

# ECS Service
resource "aws_ecs_service" "backend" {
  name            = "backend-${var.environment}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.backend.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.backend_sg_id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
}

# Allow ALB to talk to Backend
resource "aws_security_group_rule" "alb_to_backend" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = var.backend_sg_id
  source_security_group_id = aws_security_group.alb.id
}
