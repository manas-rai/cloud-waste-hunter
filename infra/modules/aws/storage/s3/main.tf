resource "aws_s3_bucket" "cloud-waste-hunter" {
  bucket = var.bucket_name
  tags   = var.tags
}

# Add standard security best practices
resource "aws_s3_bucket_public_access_block" "cloud-waste-hunter" {
  bucket = aws_s3_bucket.cloud-waste-hunter.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
