output "policy_json" {
  description = "Read-only CloudWatch and scoped Bedrock invoke policy; attach to a reviewed role."
  value = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadConfiguredLogs"
        Effect   = "Allow"
        Action   = ["logs:FilterLogEvents"]
        Resource = "arn:aws:logs:${var.region}:${var.account_id}:log-group:${var.log_group_prefix}*:*"
      },
      {
        Sid      = "InvokeConfiguredModel"
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "arn:aws:bedrock:${var.region}::foundation-model/${var.model_id}"
      }
    ]
  })
}
