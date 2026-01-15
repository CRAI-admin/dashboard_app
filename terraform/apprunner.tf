# GitHub Connection for App Runner
# NOTE: This must be created manually first via AWS Console
# Go to: App Runner -> GitHub connections -> Add connection
# After creating, update the connection ARN in terraform.tfvars

resource "aws_apprunner_service" "dashboard" {
  service_name = var.app_name

  source_configuration {
    auto_deployments_enabled = true  # Auto-deploy on git push
    
    code_repository {
      repository_url = var.github_repo_url
      
      source_code_version {
        type  = "BRANCH"
        value = var.github_branch
      }
      
      code_configuration {
        configuration_source = "API"  # Use Terraform config, not apprunner.yaml
        
        code_configuration_values {
          runtime = "PYTHON_3"
          
          build_command = "cd app && pip install -r requirements.txt"
          start_command = "cd app && streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"
          port          = "8501"
          
          runtime_environment_variables = {
            STREAMLIT_SERVER_PORT      = "8501"
            STREAMLIT_SERVER_ADDRESS   = "0.0.0.0"
            STREAMLIT_SERVER_HEADLESS  = "true"
            STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
            DASHBOARD_PASSWORD         = var.dashboard_password
          }
        }
      }
    }
    
    # You must create this connection manually first!
    # See: https://docs.aws.amazon.com/apprunner/latest/dg/manage-connections.html
    authentication_configuration {
      connection_arn = var.github_connection_arn
    }
  }

  instance_configuration {
    cpu    = var.cpu
    memory = var.memory
    
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = var.health_check_path
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.dashboard.arn

  tags = merge(
    var.tags,
    {
      Name = var.app_name
    }
  )
}

# Auto Scaling Configuration
resource "aws_apprunner_auto_scaling_configuration_version" "dashboard" {
  auto_scaling_configuration_name = "${var.app_name}-autoscaling"
  
  max_concurrency = var.auto_scaling_max_concurrency
  max_size        = var.auto_scaling_max_size
  min_size        = var.auto_scaling_min_size

  tags = merge(
    var.tags,
    {
      Name = "${var.app_name}-autoscaling"
    }
  )
}
