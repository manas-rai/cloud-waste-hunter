resource "aws_db_subnet_group" "this" {
  name       = "db-subnet-group-${var.environment}"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_db_instance" "this" {
  identifier           = "db-${var.environment}"
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "18.1"
  instance_class       = "db.t3.micro"
  db_name              = "cloudwastehunter"
  username             = var.db_username
  password             = var.db_password
  db_subnet_group_name = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  skip_final_snapshot  = true
  tags                 = var.tags
}

output "db_endpoint" {
  value = aws_db_instance.this.endpoint
}
