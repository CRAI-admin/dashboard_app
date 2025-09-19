# GitHub Actions CI/CD Setup Guide

## 1. AWS IAM Setup

### Create IAM User for GitHub Actions
```bash
# Create IAM user
aws iam create-user --user-name github-actions-cr-dashboard

# Create policy for ECS, ECR, and IAM access
aws iam create-policy --policy-name GitHubActionsCRDashboard --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::837107980418:role/StreamlitECSStack-*",
        "arn:aws:iam::837107980418:role/ecsTaskExecutionRole"
      ]
    }
  ]
}'

# Attach policy to user
aws iam attach-user-policy --user-name github-actions-cr-dashboard --policy-arn arn:aws:iam::837107980418:policy/GitHubActionsCRDashboard

# Create access keys
aws iam create-access-key --user-name github-actions-cr-dashboard
```

## 2. GitHub Repository Secrets

Add these secrets to your GitHub repository:

### Required Secrets:
1. **AWS_ACCESS_KEY_ID**: From the access key creation above
2. **AWS_SECRET_ACCESS_KEY**: From the access key creation above

### How to add secrets:
1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact names above

## 3. Deployment Workflow

### Automatic Dev Deployment:
- Push to `main` branch with changes to:
  - `streamlit_app_*.py`
  - `Dockerfile.streamlit`
  - `requirements_streamlit.txt`
  - `.github/workflows/deploy.yml`

### Manual Production Deployment:
1. Go to **Actions** tab in GitHub
2. Select **Deploy CR-AI Dashboard** workflow
3. Click **Run workflow**
4. Select **prod** environment
5. Click **Run workflow**

## 4. Monitoring Deployments

### Check deployment status:
- GitHub Actions tab shows build/deploy progress
- AWS ECS console shows service updates
- CloudWatch logs show container startup

### URLs after deployment:
- **Dev**: http://StreamlitECSStack-DEV-ALB-923328378.us-east-1.elb.amazonaws.com
- **Prod**: https://dev.cr-ai-dashboard.com

## 5. Troubleshooting

### Common issues:
1. **ECR permissions**: Ensure IAM user can push to ECR repository
2. **ECS permissions**: Ensure IAM user can update services and task definitions
3. **Task definition**: Ensure container definitions match existing setup
4. **Image build**: Check Dockerfile paths and dependencies

### Debug commands:
```bash
# Check ECS service status
aws ecs describe-services --cluster StreamlitECSStack-DEV-StreamlitCluster --services StreamlitECSStack-DEV-Service

# Check task definition
aws ecs describe-task-definition --task-definition cr-score-app-task-dev

# Check ECR repository
aws ecr describe-repositories --repository-names cr-score-app
```