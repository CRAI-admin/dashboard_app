#!/bin/bash

# Local deployment script for testing
# Usage: ./scripts/deploy-local.sh [dev|prod]

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION="us-east-1"
ECR_REPOSITORY="cr-score-app"
AWS_ACCOUNT_ID="837107980418"

# Set environment-specific variables
if [ "$ENVIRONMENT" = "prod" ]; then
    CLUSTER_NAME="StreamlitECSStack-StreamlitClusterED254C56-NEFl9DXzdcci"
    SERVICE_NAME="StreamlitECSStack-StreamlitService4F1549C0-OyxFDtrF3qPR"
    TASK_FAMILY="cr-score-app-task"
    IMAGE_TAG="local-prod-$(date +%s)"
else
    CLUSTER_NAME="StreamlitECSStack-DEV-StreamlitCluster"
    SERVICE_NAME="StreamlitECSStack-DEV-Service"
    TASK_FAMILY="cr-score-app-task-dev"
    IMAGE_TAG="local-dev-$(date +%s)"
fi

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
FULL_IMAGE_URI="$ECR_URI/$ECR_REPOSITORY:$IMAGE_TAG"

echo "🚀 Deploying to $ENVIRONMENT environment"
echo "📍 Cluster: $CLUSTER_NAME"
echo "🔧 Service: $SERVICE_NAME"
echo "🏷️  Image: $FULL_IMAGE_URI"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
echo "🐳 Building Docker image..."
docker build -f Dockerfile.streamlit -t $FULL_IMAGE_URI .

# Push image to ECR
echo "📤 Pushing image to ECR..."
docker push $FULL_IMAGE_URI

# Get current task definition
echo "📋 Getting current task definition..."
TASK_DEFINITION=$(aws ecs describe-task-definition --task-definition $TASK_FAMILY --query taskDefinition)

# Update image in task definition
echo "🔄 Updating task definition with new image..."
NEW_TASK_DEFINITION=$(echo $TASK_DEFINITION | jq --arg IMAGE "$FULL_IMAGE_URI" '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')

# Register new task definition
echo "✅ Registering new task definition..."
NEW_TASK_DEF_ARN=$(echo $NEW_TASK_DEFINITION | aws ecs register-task-definition --cli-input-json file:///dev/stdin --query 'taskDefinition.taskDefinitionArn' --output text)
echo "📝 New task definition: $NEW_TASK_DEF_ARN"

# Update ECS service
echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $NEW_TASK_DEF_ARN \
    --force-new-deployment > /dev/null

echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --cli-read-timeout 600

echo "🎉 Deployment completed successfully!"

if [ "$ENVIRONMENT" = "dev" ]; then
    echo "🔗 Dev URL: http://StreamlitECSStack-DEV-ALB-923328378.us-east-1.elb.amazonaws.com"
else
    echo "🔗 Prod URL: https://dev.cr-ai-dashboard.com"
fi