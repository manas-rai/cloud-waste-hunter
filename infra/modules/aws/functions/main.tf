resource "aws_lambda_function" "this" {
  function_name = "${var.function_name}-${var.environment}"
  role          = var.app_role_arn
  handler       = var.handler
  runtime       = var.runtime
  filename      = var.filename

  # Only include vpc_config if subnets are provided
  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  environment {
    variables = var.environment_variables
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = 7
  tags              = var.tags
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}
