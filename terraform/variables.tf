variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., demo, prod)"
  type        = string
  default     = "demo"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "crscore-dashboard-construction"
}

variable "github_repo_url" {
  description = "GitHub repository URL (format: https://github.com/owner/repo)"
  type        = string
  # You'll set this in terraform.tfvars
}

variable "github_branch" {
  description = "GitHub branch to deploy from"
  type        = string
  default     = "main"
}

variable "github_connection_arn" {
  description = "ARN of the GitHub connection (must be created manually in AWS Console first)"
  type        = string
  # You'll set this in terraform.tfvars after creating the connection
}

variable "dashboard_password" {
  description = "Password for dashboard access (sensitive)"
  type        = string
  sensitive   = true
  # You'll set this in terraform.tfvars
}

variable "cpu" {
  description = "CPU units for the App Runner service (256 = 0.25 vCPU, 1024 = 1 vCPU, 2048 = 2 vCPU, 4096 = 4 vCPU)"
  type        = string
  default     = "1024"  # 1 vCPU
}

variable "memory" {
  description = "Memory for the App Runner service (in MB: 512, 1024, 2048, 3072, 4096, 6144, 8192, 10240, 12288)"
  type        = string
  default     = "2048"  # 2 GB
}

variable "auto_scaling_max_concurrency" {
  description = "Maximum number of concurrent requests per instance"
  type        = number
  default     = 10  # Low for demo usage
}

variable "auto_scaling_max_size" {
  description = "Maximum number of instances"
  type        = number
  default     = 2  # Maximum 2 instances for cost control
}

variable "auto_scaling_min_size" {
  description = "Minimum number of instances"
  type        = number
  default     = 1  # Keep 1 instance running
}

variable "health_check_path" {
  description = "Health check path for App Runner"
  type        = string
  default     = "/_stcore/health"
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
