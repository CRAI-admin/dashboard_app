#!/bin/bash

# Status checking script
# Usage: ./scripts/status.sh [dev|prod]

ENVIRONMENT=${1:-dev}

# Set environment-specific variables
if [ "$ENVIRONMENT" = "prod" ]; then
    CLUSTER_NAME="StreamlitECSStack-StreamlitClusterED254C56-NEFl9DXzdcci"
    SERVICE_NAME="StreamlitECSStack-StreamlitService4F1549C0-OyxFDtrF3qPR"
    TASK_FAMILY="cr-score-app-task"
    URL="https://dev.cr-ai-dashboard.com"
else
    CLUSTER_NAME="StreamlitECSStack-DEV-StreamlitCluster"
    SERVICE_NAME="StreamlitECSStack-DEV-Service"
    TASK_FAMILY="cr-score-app-task-dev"
    URL="http://StreamlitECSStack-DEV-ALB-923328378.us-east-1.elb.amazonaws.com"
fi

echo "📊 Status for $ENVIRONMENT environment"
echo "=================================="

# Service status
echo "🔧 Service Status:"
SERVICE_STATUS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].[status,desiredCount,runningCount,pendingCount]' --output table)
echo "$SERVICE_STATUS"

# Task definition info
echo ""
echo "📋 Current Task Definition:"
TASK_DEF_INFO=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].taskDefinition' --output text)
echo "Task Definition ARN: $TASK_DEF_INFO"

# Get image from current task definition
CURRENT_IMAGE=$(aws ecs describe-task-definition --task-definition $TASK_DEF_INFO --query 'taskDefinition.containerDefinitions[0].image' --output text)
echo "Current Image: $CURRENT_IMAGE"

# Recent deployments
echo ""
echo "🚀 Recent Deployments:"
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --query 'services[0].deployments[*].[status,taskDefinition,createdAt,updatedAt]' --output table

# Task definition revisions
echo ""
echo "📚 Recent Task Definition Revisions:"
aws ecs list-task-definitions --family-prefix $TASK_FAMILY --sort DESC --max-items 5 --query 'taskDefinitionArns' --output table

# Health check
echo ""
echo "🏥 Health Check:"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $URL/_stcore/health 2>/dev/null || echo "FAILED")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Application is healthy (HTTP $HTTP_STATUS)"
else
    echo "❌ Application health check failed (HTTP $HTTP_STATUS)"
fi

echo ""
echo "🔗 Application URL: $URL"