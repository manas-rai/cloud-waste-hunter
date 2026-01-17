aws_region  = "ap-south-1"
environment = "dev"

# Storage
bucket_name = "cloud-waste-hunter-dev"

# Tags
tags = {
  Environment = "dev"
  Project     = "cloud-waste-hunter"
  ManagedBy   = "Manas Rai"
}

# Database
db_username = "dbadmin"
db_password = "manasmr@4133" # In real use, pass this via CLI or Secret Manager

# Compute
backend_image = "public.ecr.aws/nginx/nginx:latest" # Placeholder image for testing
