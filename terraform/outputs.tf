output "app_runner_service_url" {
  description = "URL of the App Runner service - share this with your 2 users"
  value       = aws_apprunner_service.dashboard.service_url
}

output "app_runner_service_id" {
  description = "ID of the App Runner service"
  value       = aws_apprunner_service.dashboard.service_id
}

output "app_runner_service_arn" {
  description = "ARN of the App Runner service"
  value       = aws_apprunner_service.dashboard.service_arn
}

output "app_runner_status" {
  description = "Status of the App Runner service"
  value       = aws_apprunner_service.dashboard.status
}

output "dashboard_access_instructions" {
  description = "Instructions for accessing the dashboard"
  value       = <<-EOT
    
    ═══════════════════════════════════════════════════════════
    🎉 DASHBOARD DEPLOYMENT COMPLETE!
    ═══════════════════════════════════════════════════════════
    
    📍 Dashboard URL: https://${aws_apprunner_service.dashboard.service_url}
    
    🔐 Login Password: ${var.dashboard_password}
    
    👥 Share this URL with your 2 users:
       https://${aws_apprunner_service.dashboard.service_url}
    
    ⏰ The app is now running 24/7 on AWS App Runner
    
    💰 Estimated monthly cost: $5-15 (based on usage)
    
    📊 To monitor your app:
       AWS Console → App Runner → ${var.app_name}
    
    ═══════════════════════════════════════════════════════════
  EOT
  sensitive = false
}
