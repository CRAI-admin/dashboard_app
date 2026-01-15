# ═══════════════════════════════════════════════════════════════════════════
# Pre-Flight Checklist - Run this BEFORE deploying
# This script checks for common issues that would cause deployment to fail
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           Pre-Flight Deployment Checklist                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
" -ForegroundColor Cyan

$allChecksPass = $true

# Check 1: AWS CLI and Credentials
Write-Host "`n[1/10] Checking AWS CLI and credentials..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS configured - Account: $($identity.Account), User: $($identity.Arn)" -ForegroundColor Green
    
    # Check permissions
    Write-Host "   Testing IAM permissions..." -ForegroundColor Gray
    $canCreateRole = aws iam list-roles --max-items 1 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Can access IAM" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Cannot access IAM - you may lack permissions" -ForegroundColor Yellow
        $allChecksPass = $false
    }
} catch {
    Write-Host "❌ AWS CLI not configured or not working" -ForegroundColor Red
    Write-Host "   Fix: Run 'aws configure'" -ForegroundColor Yellow
    $allChecksPass = $false
}

# Check 2: Terraform
Write-Host "`n[2/10] Checking Terraform..." -ForegroundColor Yellow
try {
    $tfVersion = terraform version -json | ConvertFrom-Json
    Write-Host "✅ Terraform $($tfVersion.terraform_version) installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Terraform not installed" -ForegroundColor Red
    Write-Host "   Fix: Download from https://www.terraform.io/downloads" -ForegroundColor Yellow
    $allChecksPass = $false
}

# Check 3: Git
Write-Host "`n[3/10] Checking Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "✅ $gitVersion" -ForegroundColor Green
    
    # Check if repo is initialized
    if (Test-Path ".git") {
        Write-Host "   ✅ Git repository initialized" -ForegroundColor Green
        
        # Check for remote
        $remote = git remote get-url origin 2>$null
        if ($remote) {
            Write-Host "   ✅ Remote configured: $remote" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  No remote configured" -ForegroundColor Yellow
            Write-Host "      You need to push to GitHub before deploying" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  Git not initialized" -ForegroundColor Yellow
        Write-Host "      Run: git init" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Git not installed" -ForegroundColor Red
    $allChecksPass = $false
}

# Check 4: App files
Write-Host "`n[4/10] Checking app files..." -ForegroundColor Yellow
$appFiles = @(
    "app/streamlit_app.py",
    "app/requirements.txt",
    "app/Dockerfile"
)

foreach ($file in $appFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        $allChecksPass = $false
    }
}

# Check 5: CSV files
Write-Host "`n[5/10] Checking CSV data files..." -ForegroundColor Yellow
$csvFiles = Get-ChildItem -Path "app" -Filter "*.csv" -ErrorAction SilentlyContinue
$expectedCSVs = @(
    "executive_summary.csv",
    "bidding_processes.csv",
    "bidding_kpis.csv",
    "preconstruction_processes.csv",
    "preconstruction_kpis.csv",
    "construction_processes.csv",
    "construction_kpis.csv",
    "closeout_processes.csv",
    "closeout_kpis.csv",
    "procore-itemized-combined.csv"
)

if ($csvFiles.Count -ge 10) {
    Write-Host "✅ Found $($csvFiles.Count) CSV files" -ForegroundColor Green
    
    # Check for specific files
    foreach ($csv in $expectedCSVs) {
        if (Test-Path "app/$csv") {
            Write-Host "   ✅ $csv" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Missing: $csv" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ Only found $($csvFiles.Count) CSV files (expected 10)" -ForegroundColor Red
    $allChecksPass = $false
}

# Check 6: Terraform files
Write-Host "`n[6/10] Checking Terraform files..." -ForegroundColor Yellow
$tfFiles = @(
    "terraform/main.tf",
    "terraform/variables.tf",
    "terraform/iam.tf",
    "terraform/apprunner.tf",
    "terraform/outputs.tf"
)

foreach ($file in $tfFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        $allChecksPass = $false
    }
}

# Check 7: terraform.tfvars
Write-Host "`n[7/10] Checking terraform.tfvars..." -ForegroundColor Yellow
if (Test-Path "terraform/terraform.tfvars") {
    Write-Host "✅ terraform.tfvars exists" -ForegroundColor Green
    
    # Check for required values
    $tfvarsContent = Get-Content "terraform/terraform.tfvars" -Raw
    
    $checks = @{
        "github_repo_url" = "GitHub repo URL"
        "github_connection_arn" = "GitHub connection ARN"
        "dashboard_password" = "Dashboard password"
    }
    
    foreach ($key in $checks.Keys) {
        if ($tfvarsContent -match "$key\s*=\s*`"[^`"]+`"") {
            $value = ($tfvarsContent | Select-String -Pattern "$key\s*=\s*`"([^`"]+)`"").Matches.Groups[1].Value
            
            if ($value -match "YOUR_|CHANGE_|EXAMPLE") {
                Write-Host "   ⚠️  $($checks[$key]) needs to be updated" -ForegroundColor Yellow
                $allChecksPass = $false
            } elseif ($key -eq "github_connection_arn" -and $value -notmatch "arn:aws:apprunner") {
                Write-Host "   ⚠️  GitHub connection ARN looks invalid" -ForegroundColor Yellow
                $allChecksPass = $false
            } else {
                Write-Host "   ✅ $($checks[$key]) is set" -ForegroundColor Green
            }
        } else {
            Write-Host "   ❌ $($checks[$key]) is missing" -ForegroundColor Red
            $allChecksPass = $false
        }
    }
} else {
    Write-Host "❌ terraform.tfvars not found" -ForegroundColor Red
    Write-Host "   Fix: Copy terraform.tfvars.example to terraform.tfvars and edit it" -ForegroundColor Yellow
    $allChecksPass = $false
}

# Check 8: S3 Bucket
Write-Host "`n[8/10] Checking S3 bucket for Terraform state..." -ForegroundColor Yellow
try {
    $bucketExists = aws s3api head-bucket --bucket "crai-dashboard-terraform-state" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ S3 bucket exists" -ForegroundColor Green
    } else {
        Write-Host "⚠️  S3 bucket doesn't exist yet (will be created during deployment)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Cannot check S3 bucket" -ForegroundColor Yellow
}

# Check 9: GitHub Connection
Write-Host "`n[9/10] Checking GitHub connection..." -ForegroundColor Yellow
if (Test-Path "terraform/terraform.tfvars") {
    $tfvarsContent = Get-Content "terraform/terraform.tfvars" -Raw
    if ($tfvarsContent -match 'github_connection_arn\s*=\s*"(arn:aws:apprunner[^"]+)"') {
        $connArn = $matches[1]
        Write-Host "   Found connection ARN: $connArn" -ForegroundColor Gray
        
        # Try to verify it exists
        try {
            $connCheck = aws apprunner list-connections --output json 2>$null | ConvertFrom-Json
            if ($connCheck.ConnectionSummaryList | Where-Object {$_.ConnectionArn -eq $connArn}) {
                Write-Host "✅ GitHub connection verified in AWS" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Cannot verify GitHub connection (may not exist yet)" -ForegroundColor Yellow
                Write-Host "   Create it: AWS Console → App Runner → GitHub connections" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "⚠️  Cannot list connections (need to create manually)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ GitHub connection ARN not configured" -ForegroundColor Red
        Write-Host "   You MUST create this in AWS Console first!" -ForegroundColor Red
        $allChecksPass = $false
    }
}

# Check 10: Code pushed to GitHub
Write-Host "`n[10/10] Checking if code is pushed to GitHub..." -ForegroundColor Yellow
if (Test-Path ".git") {
    $status = git status --porcelain
    if ($status) {
        Write-Host "⚠️  You have uncommitted changes" -ForegroundColor Yellow
        Write-Host "   Commit and push before deploying" -ForegroundColor Yellow
    } else {
        Write-Host "✅ No uncommitted changes" -ForegroundColor Green
    }
    
    # Check if pushed
    $branch = git branch --show-current
    $remote = git remote get-url origin 2>$null
    if ($remote) {
        Write-Host "   Branch: $branch" -ForegroundColor Gray
        Write-Host "   Remote: $remote" -ForegroundColor Gray
        Write-Host "   ⚠️  Make sure you've pushed to GitHub!" -ForegroundColor Yellow
    }
}

# Final Summary
Write-Host "`n" -NoNewline
Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Cyan
if ($allChecksPass) {
    Write-Host "✅ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You're ready to deploy! Run:" -ForegroundColor Green
    Write-Host "   .\deploy.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or manually:" -ForegroundColor Green
    Write-Host "   cd terraform" -ForegroundColor Cyan
    Write-Host "   terraform init" -ForegroundColor Cyan
    Write-Host "   terraform plan" -ForegroundColor Cyan
    Write-Host "   terraform apply" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  SOME CHECKS FAILED" -ForegroundColor Yellow
    Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Please fix the issues above before deploying." -ForegroundColor Yellow
    Write-Host "Review the warnings and errors, then run this script again." -ForegroundColor Yellow
}
Write-Host ""
