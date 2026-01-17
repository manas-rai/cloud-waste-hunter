terraform {
  required_version = ">= 1.14.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.18.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Networking
module "networking" {
  source      = "./modules/aws/networking"
  environment = var.environment
  tags        = var.tags
  # Using defaults for CIDRs, but can be overridden here
}

# 2. Security (IAM & SGs)
module "security" {
  source      = "./modules/aws/security"
  vpc_id      = module.networking.vpc_id
  environment = var.environment
  tags        = var.tags
}

# 3. Storage
module "s3_bucket" {
  source      = "./modules/aws/storage/s3"
  bucket_name = var.bucket_name
  tags        = var.tags
}
/*
# 4. Database
module "database" {
  source             = "./modules/aws/database"
  environment        = var.environment
  subnet_ids         = module.networking.private_subnet_ids
  security_group_ids = [module.security.db_sg_id]
  db_username        = var.db_username
  db_password        = var.db_password
  tags               = var.tags
}
*/
/*
# 5. Compute (ECS Fargate)
module "compute" {
  source             = "./modules/aws/compute"
  environment        = var.environment
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  private_subnet_ids = module.networking.private_subnet_ids
  backend_sg_id      = module.security.backend_sg_id
  app_role_arn       = module.security.app_role_arn
  backend_image      = var.backend_image
  db_url             = "postgresql://${var.db_username}:${var.db_password}@${module.database.db_endpoint}/cloudwastehunter"
  tags               = var.tags
}
*/
