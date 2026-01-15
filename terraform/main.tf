terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 Backend for Terraform State
  backend "s3" {
    bucket         = "crai-dashboard-terraform-state"  # Will be created separately
    key            = "dashboard/construction-demo/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"  # Optional: for state locking
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "CR-Score Dashboard"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Application = "Construction Demo"
    }
  }
}
