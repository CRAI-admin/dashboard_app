# IAM Role for App Runner Service
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.app_name}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-instance-role"
    }
  )
}

# Policy for CloudWatch Logs (if needed for debugging)
resource "aws_iam_role_policy" "apprunner_cloudwatch" {
  name = "${var.app_name}-cloudwatch-policy"
  role = aws_iam_role.apprunner_instance_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/apprunner/${var.app_name}/*"
      }
    ]
  })
}

# IAM Role for App Runner to access ECR (for building from source)
resource "aws_iam_role" "apprunner_build_role" {
  name = "${var.app_name}-build-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-build-role"
    }
  )
}

# Attach AWS managed policy for ECR access
resource "aws_iam_role_policy_attachment" "apprunner_build_ecr" {
  role       = aws_iam_role.apprunner_build_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}
