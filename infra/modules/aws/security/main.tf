# IAM Role for ECS/Lambda
resource "aws_iam_role" "app_role" {
  name = "app-role-${var.environment}"
  tags = var.tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["ecs-tasks.amazonaws.com", "lambda.amazonaws.com"]
        }
      }
    ]
  })
}
/*
resource "aws_iam_role_policy" "bedrock" {
  name = "bedrock-access-${var.environment}"
  role = aws_iam_role.app_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "bedrock:*"
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}
*/

# Standard Security Groups
resource "aws_security_group" "backend" {
  name        = "backend-sg-${var.environment}"
  vpc_id      = var.vpc_id
  description = "SG for FastAPI backend"
  tags        = var.tags

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name        = "db-sg-${var.environment}"
  vpc_id      = var.vpc_id
  description = "SG for RDS database"
  tags        = var.tags

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Rule to allow backend to talk to DB
resource "aws_security_group_rule" "backend_to_db" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.backend.id
}

output "app_role_arn" {
  value = aws_iam_role.app_role.arn
}

output "backend_sg_id" {
  value = aws_security_group.backend.id
}

output "db_sg_id" {
  value = aws_security_group.db.id
}
