# PowerShell deployment script for Windows
# Usage: .\scripts\deploy-local.ps1 [dev|prod]

param(
    [Parameter(Position=0)]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"

$AWS_REGION = "us-east-1"
$ECR_REPOSITORY = "cr-score-app"
$AWS_ACCOUNT_ID = "837107980418"

# Set environment-specific variables
if ($Environment -eq "prod") {
    $CLUSTER_NAME = "StreamlitECSStack-StreamlitClusterED254C56-NEFl9DXzdcci"
    $SERVICE_NAME = "StreamlitECSStack-StreamlitService4F1549C0-OyxFDtrF3qPR"
    $TASK_FAMILY = "cr-score-app-task"
    $IMAGE_TAG = "local-prod-$(Get-Date -Format 'yyyyMMddHHmmss')"
} else {
    $CLUSTER_NAME = "StreamlitECSStack-DEV-StreamlitCluster"
    $SERVICE_NAME = "StreamlitECSStack-DEV-Service"
    $TASK_FAMILY = "cr-score-app-task-dev"
    $IMAGE_TAG = "local-dev-$(Get-Date -Format 'yyyyMMddHHmmss')"
}

$ECR_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
$FULL_IMAGE_URI = "$ECR_URI/$ECR_REPOSITORY`:$IMAGE_TAG"

Write-Host "🚀 Deploying to $Environment environment" -ForegroundColor Green
Write-Host "📍 Cluster: $CLUSTER_NAME" -ForegroundColor Cyan
Write-Host "🔧 Service: $SERVICE_NAME" -ForegroundColor Cyan
Write-Host "🏷️  Image: $FULL_IMAGE_URI" -ForegroundColor Cyan

# Check if AWS CLI is configured
try {
    aws sts get-caller-identity | Out-Null
} catch {
    Write-Host "❌ AWS CLI not configured. Please run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Login to ECR
Write-Host "🔐 Logging in to ECR..." -ForegroundColor Yellow
$loginCommand = aws ecr get-login-password --region $AWS_REGION
$loginCommand | docker login --username AWS --password-stdin $ECR_URI

# Build Docker image
Write-Host "🐳 Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.streamlit -t $FULL_IMAGE_URI .

# Push image to ECR
Write-Host "📤 Pushing image to ECR..." -ForegroundColor Yellow
docker push $FULL_IMAGE_URI

# Get current task definition
Write-Host "📋 Getting current task definition..." -ForegroundColor Yellow
$taskDefinition = aws ecs describe-task-definition --task-definition $TASK_FAMILY --query taskDefinition | ConvertFrom-Json

# Update image in task definition
Write-Host "🔄 Updating task definition with new image..." -ForegroundColor Yellow
$taskDefinition.containerDefinitions[0].image = $FULL_IMAGE_URI

# Remove fields not needed for registration
$taskDefinition.PSObject.Properties.Remove('taskDefinitionArn')
$taskDefinition.PSObject.Properties.Remove('revision')
$taskDefinition.PSObject.Properties.Remove('status')
$taskDefinition.PSObject.Properties.Remove('requiresAttributes')
$taskDefinition.PSObject.Properties.Remove('placementConstraints')
$taskDefinition.PSObject.Properties.Remove('compatibilities')
$taskDefinition.PSObject.Properties.Remove('registeredAt')
$taskDefinition.PSObject.Properties.Remove('registeredBy')

# Convert to JSON and save to temp file
$tempFile = [System.IO.Path]::GetTempFileName()
$taskDefinition | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8

# Register new task definition
Write-Host "✅ Registering new task definition..." -ForegroundColor Yellow
$newTaskDefArn = aws ecs register-task-definition --cli-input-json "file://$tempFile" --query 'taskDefinition.taskDefinitionArn' --output text
Write-Host "📝 New task definition: $newTaskDefArn" -ForegroundColor Green

# Clean up temp file
Remove-Item $tempFile

# Update ECS service
Write-Host "🔄 Updating ECS service..." -ForegroundColor Yellow
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --task-definition $newTaskDefArn --force-new-deployment | Out-Null

Write-Host "⏳ Waiting for deployment to complete..." -ForegroundColor Yellow
try {
    aws ecs wait services-stable --cluster $CLUSTER_NAME --services $SERVICE_NAME --cli-read-timeout 600
    Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Deployment initiated but may still be in progress. Check AWS console for status." -ForegroundColor Yellow
}

if ($Environment -eq "dev") {
    Write-Host "🔗 Dev URL: http://StreamlitECSStack-DEV-ALB-923328378.us-east-1.elb.amazonaws.com" -ForegroundColor Cyan
} else {
    Write-Host "🔗 Prod URL: https://dev.cr-ai-dashboard.com" -ForegroundColor Cyan
}