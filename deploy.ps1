# ═══════════════════════════════════════════════════════════════════════════
# CR-Score Dashboard - Quick Deployment Script
# Run this script to deploy your dashboard to AWS App Runner
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        CR-Score Dashboard - AWS App Runner Deployment         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
" -ForegroundColor Cyan

# Set error handling
$ErrorActionPreference = "Stop"

# Configuration
$TERRAFORM_DIR = "terraform"
$APP_DIR = "app"
$STATE_BUCKET = "crai-dashboard-terraform-state"
$AWS_REGION = "us-east-1"

# Step 1: Prerequisites Check
Write-Host "`n[Step 1/6] Checking prerequisites..." -ForegroundColor Yellow

# Check AWS CLI
try {
    $awsIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured - Account: $($awsIdentity.Account)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run: aws configure" -ForegroundColor Red
    exit 1
}

# Check Terraform
try {
    $tfVersion = terraform version | Select-String -Pattern "Terraform v"
    Write-Host "✅ Terraform installed - $tfVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Terraform not installed. Download from: https://www.terraform.io/downloads" -ForegroundColor Red
    exit 1
}

# Check Git
try {
    $gitVersion = git --version
    Write-Host "✅ Git installed - $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git not installed. Download from: https://git-scm.com/" -ForegroundColor Red
    exit 1
}

# Step 2: Create S3 Bucket for Terraform State
Write-Host "`n[Step 2/6] Creating S3 bucket for Terraform state..." -ForegroundColor Yellow

try {
    # Check if bucket exists
    $bucketExists = aws s3api head-bucket --bucket $STATE_BUCKET 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ S3 bucket already exists: $STATE_BUCKET" -ForegroundColor Green
    } else {
        # Create bucket
        aws s3api create-bucket --bucket $STATE_BUCKET --region $AWS_REGION
        
        # Enable versioning
        aws s3api put-bucket-versioning --bucket $STATE_BUCKET --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption --bucket $STATE_BUCKET --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}'
        
        Write-Host "✅ S3 bucket created: $STATE_BUCKET" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Could not create/access S3 bucket. It may already exist or you may not have permissions." -ForegroundColor Yellow
}

# Step 3: Verify Files
Write-Host "`n[Step 3/6] Verifying files..." -ForegroundColor Yellow

# Check app files
$requiredAppFiles = @(
    "$APP_DIR/streamlit_app.py",
    "$APP_DIR/requirements.txt",
    "$APP_DIR/Dockerfile"
)

foreach ($file in $requiredAppFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        exit 1
    }
}

# Check CSV files
$csvFiles = Get-ChildItem -Path $APP_DIR -Filter "*.csv"
if ($csvFiles.Count -ge 10) {
    Write-Host "✅ Found $($csvFiles.Count) CSV files" -ForegroundColor Green
} else {
    Write-Host "❌ Missing CSV files. Expected 10, found $($csvFiles.Count)" -ForegroundColor Red
    exit 1
}

# Check Terraform files
$requiredTfFiles = @(
    "$TERRAFORM_DIR/main.tf",
    "$TERRAFORM_DIR/variables.tf",
    "$TERRAFORM_DIR/iam.tf",
    "$TERRAFORM_DIR/apprunner.tf",
    "$TERRAFORM_DIR/outputs.tf"
)

foreach ($file in $requiredTfFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        exit 1
    }
}

# Step 4: Configure Terraform
Write-Host "`n[Step 4/6] Configuring Terraform..." -ForegroundColor Yellow

if (-not (Test-Path "$TERRAFORM_DIR/terraform.tfvars")) {
    if (Test-Path "$TERRAFORM_DIR/terraform.tfvars.example") {
        Copy-Item "$TERRAFORM_DIR/terraform.tfvars.example" "$TERRAFORM_DIR/terraform.tfvars"
        Write-Host "⚠️  Created terraform.tfvars from example" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📝 ACTION REQUIRED:" -ForegroundColor Red
        Write-Host "   1. Create GitHub connection in AWS Console:" -ForegroundColor White
        Write-Host "      AWS Console → App Runner → GitHub connections → Add connection" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "   2. Edit terraform/terraform.tfvars and update:" -ForegroundColor White
        Write-Host "      - github_repo_url" -ForegroundColor Cyan
        Write-Host "      - github_connection_arn (from step 1)" -ForegroundColor Cyan
        Write-Host "      - dashboard_password" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "   3. Run this script again after updating terraform.tfvars" -ForegroundColor White
        Write-Host ""
        
        # Open the file for editing
        notepad "$TERRAFORM_DIR/terraform.tfvars"
        exit 0
    } else {
        Write-Host "❌ terraform.tfvars.example not found" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ terraform.tfvars exists" -ForegroundColor Green

# Step 5: Initialize Terraform
Write-Host "`n[Step 5/6] Initializing Terraform..." -ForegroundColor Yellow

Set-Location $TERRAFORM_DIR

try {
    terraform init
    Write-Host "✅ Terraform initialized" -ForegroundColor Green
} catch {
    Write-Host "❌ Terraform initialization failed" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Step 6: Deploy
Write-Host "`n[Step 6/6] Ready to deploy!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Review the deployment plan:" -ForegroundColor White
Write-Host ""

terraform plan

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Ready to deploy your dashboard to AWS App Runner?" -ForegroundColor Yellow
Write-Host "This will:" -ForegroundColor White
Write-Host "  • Create IAM roles" -ForegroundColor Cyan
Write-Host "  • Deploy App Runner service" -ForegroundColor Cyan
Write-Host "  • Build and run your Streamlit dashboard" -ForegroundColor Cyan
Write-Host "  • Estimated time: 8-10 minutes" -ForegroundColor Cyan
Write-Host "  • Estimated cost: ~`$6-11/month" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "Type 'yes' to deploy, or 'no' to cancel"

if ($confirm -eq "yes") {
    Write-Host "`n🚀 Deploying..." -ForegroundColor Green
    
    terraform apply -auto-approve
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "🎉 DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
        Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        
        terraform output dashboard_access_instructions
        
        Write-Host ""
        Write-Host "📋 Next Steps:" -ForegroundColor Yellow
        Write-Host "  1. Open the dashboard URL in your browser" -ForegroundColor White
        Write-Host "  2. Enter the password to access" -ForegroundColor White
        Write-Host "  3. Share the URL and password with your 2 users" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "❌ Deployment failed. Check the error messages above." -ForegroundColor Red
    }
} else {
    Write-Host "❌ Deployment cancelled" -ForegroundColor Yellow
}

Set-Location ..
