#!/bin/bash

# Rollback script for emergency rollbacks
# Usage: ./scripts/rollback.sh [dev|prod] [revision_number]

set -e

ENVIRONMENT=${1:-dev}
REVISION=${2}

if [ -z "$REVISION" ]; then
    echo "❌ Error: Please specify revision number to rollback to"
    echo "Usage: ./scripts/rollback.sh [dev|prod] [revision_number]"
    exit 1
fi

# Set environment-specific variables
if [ "$ENVIRONMENT" = "prod" ]; then
    CLUSTER_NAME="StreamlitECSStack-StreamlitClusterED254C56-NEFl9DXzdcci"
    SERVICE_NAME="StreamlitECSStack-StreamlitService4F1549C0-OyxFDtrF3qPR"
    TASK_FAMILY="cr-score-app-task"
else
    CLUSTER_NAME="StreamlitECSStack-DEV-StreamlitCluster"
    SERVICE_NAME="StreamlitECSStack-DEV-Service"
    TASK_FAMILY="cr-score-app-task-dev"
fi

TASK_DEFINITION="$TASK_FAMILY:$REVISION"

echo "🔄 Rolling back $ENVIRONMENT to task definition revision $REVISION"
echo "📍 Cluster: $CLUSTER_NAME"
echo "🔧 Service: $SERVICE_NAME"
echo "📋 Task Definition: $TASK_DEFINITION"

# Check if task definition exists
if ! aws ecs describe-task-definition --task-definition $TASK_DEFINITION > /dev/null 2>&1; then
    echo "❌ Error: Task definition $TASK_DEFINITION not found"
    exit 1
fi

# Update service to use the specified task definition
echo "🔄 Updating service to use task definition $TASK_DEFINITION..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $TASK_DEFINITION \
    --force-new-deployment > /dev/null

echo "⏳ Waiting for rollback to complete..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --cli-read-timeout 600

echo "✅ Rollback completed successfully!"

if [ "$ENVIRONMENT" = "dev" ]; then
    echo "🔗 Dev URL: http://StreamlitECSStack-DEV-ALB-923328378.us-east-1.elb.amazonaws.com"
else
    echo "🔗 Prod URL: https://dev.cr-ai-dashboard.com"
fi