# 🚀 CR-Score Dashboard - AWS App Runner Deployment Guide

## 📋 Overview

This guide will help you deploy your Streamlit dashboard to AWS App Runner using Terraform (Infrastructure as Code). The entire setup takes **~30 minutes**.

---

## ✅ Prerequisites

Before starting, ensure you have:

- [ ] **AWS Account** with admin access
- [ ] **AWS CLI** installed and configured (`aws configure`)
- [ ] **Terraform** installed (v1.0+) - [Download here](https://www.terraform.io/downloads)
- [ ] **Git** installed
- [ ] **GitHub account** with this repository pushed
- [ ] **PowerShell** or terminal access

---

## 📁 Project Structure

```
dashboard_app/
├── app/                          # Application files
│   ├── streamlit_app.py         # Main dashboard (with password auth)
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Container definition
│   └── *.csv (10 files)        # Data files
│
├── terraform/                   # Infrastructure as Code
│   ├── main.tf                 # Provider & backend config
│   ├── variables.tf            # Input variables
│   ├── iam.tf                  # IAM roles & policies
│   ├── apprunner.tf            # App Runner service
│   ├── outputs.tf              # Outputs (URL, etc.)
│   └── terraform.tfvars.example # Template for your values
│
└── README_DEPLOYMENT.md        # This file
```

---

## 🔧 Step-by-Step Deployment

### **Step 1: Create S3 Bucket for Terraform State** (5 minutes)

Terraform needs a place to store its state file. Create an S3 bucket:

```powershell
# Navigate to terraform directory
cd "C:\Users\Jeremiah\Desktop\cr ai work\Bidding\dashboard_app\terraform"

# Create S3 bucket for Terraform state
aws s3api create-bucket --bucket crai-dashboard-terraform-state --region us-east-1

# Enable versioning (recommended for state file safety)
aws s3api put-bucket-versioning --bucket crai-dashboard-terraform-state --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption --bucket crai-dashboard-terraform-state --server-side-encryption-configuration '{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"}}]}'
```

**✅ Checkpoint:** Bucket created successfully

---

### **Step 2: Push Code to GitHub** (5 minutes)

Your app must be in GitHub for App Runner to deploy it.

```powershell
# Navigate to dashboard_app folder
cd "C:\Users\Jeremiah\Desktop\cr ai work\Bidding\dashboard_app"

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - CR-Score Dashboard for App Runner"

# Add remote (replace with your actual repo URL)
git remote add origin https://github.com/CRAI-admin/dashboard_app.git

# Push to main branch
git push -u origin main
```

**✅ Checkpoint:** Code is on GitHub

---

### **Step 3: Create GitHub Connection in AWS** (5 minutes)

App Runner needs permission to access your GitHub repo.

1. **Go to AWS Console**
2. **Navigate to:** App Runner → Settings → GitHub connections
3. **Click:** "Add connection"
4. **Name it:** `crai-github-connection`
5. **Authorize GitHub:** Follow the OAuth flow
6. **Copy the Connection ARN** - looks like:
   ```
   arn:aws:apprunner:us-east-1:123456789012:connection/crai-github-connection/abc123def456
   ```

**✅ Checkpoint:** GitHub connection created, ARN copied

---

### **Step 4: Configure Terraform** (5 minutes)

```powershell
# Navigate to terraform directory
cd terraform

# Copy the example config
Copy-Item terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
notepad terraform.tfvars
```

**Update these values in `terraform.tfvars`:**

```hcl
# Your GitHub repo URL
github_repo_url = "https://github.com/CRAI-admin/dashboard_app"

# The GitHub connection ARN from Step 3
github_connection_arn = "arn:aws:apprunner:us-east-1:XXXXX:connection/..."

# Password for dashboard access (change this!)
dashboard_password = "YourSecurePassword123!"

# Keep the rest as defaults or adjust as needed
```

**✅ Checkpoint:** `terraform.tfvars` configured

---

### **Step 5: Deploy with Terraform** (10 minutes)

```powershell
# Initialize Terraform (downloads providers, configures backend)
terraform init

# Preview what will be created
terraform plan

# Review the output - should show:
# - IAM roles
# - App Runner service
# - Auto-scaling configuration

# Deploy! (type 'yes' when prompted)
terraform apply
```

**What Terraform creates:**
- ✅ IAM roles for App Runner
- ✅ App Runner service (builds and deploys your app)
- ✅ Auto-scaling configuration
- ✅ Health checks

**⏱️ This takes ~8-10 minutes** (App Runner builds your container)

**✅ Checkpoint:** Terraform apply successful

---

### **Step 6: Get Your Dashboard URL** (1 minute)

After deployment completes, Terraform will display:

```
Outputs:

dashboard_access_instructions = <<EOT
    
═══════════════════════════════════════════════════════════
🎉 DASHBOARD DEPLOYMENT COMPLETE!
═══════════════════════════════════════════════════════════

📍 Dashboard URL: https://abc123xyz.us-east-1.awsapprunner.com

🔐 Login Password: YourSecurePassword123!

👥 Share this URL with your 2 users

⏰ The app is now running 24/7 on AWS App Runner

💰 Estimated monthly cost: $5-15 (based on usage)

═══════════════════════════════════════════════════════════
EOT

app_runner_service_url = "abc123xyz.us-east-1.awsapprunner.com"
```

**✅ Checkpoint:** Dashboard is live!

---

## 🎉 Testing Your Dashboard

1. **Open the URL** in your browser
2. **You should see a login screen:**
   - Enter the password from `terraform.tfvars`
3. **After login:** Full dashboard appears
4. **Test navigation:** Executive Summary, Bidding, Preconstruction, Construction, Closeout

---

## 👥 Sharing with Your 2 Users

Send them:
```
🔗 Dashboard URL: https://YOUR-APP-URL.awsapprunner.com
🔐 Password: YourSecurePassword123!

Instructions:
1. Click the link
2. Enter the password
3. Explore the dashboard!
```

---

## 💰 Cost Breakdown

| Resource | Monthly Cost |
|----------|--------------|
| App Runner (1 vCPU, 2GB RAM) | $5-10 |
| Data Transfer | <$1 |
| S3 (Terraform state) | <$0.10 |
| **Total** | **~$6-11/month** |

**Cost Control Tips:**
- Set `auto_scaling_min_size = 0` in `terraform.tfvars` to pause when not in use (saves ~50%)
- Monitor usage in AWS Cost Explorer

---

## 🔧 Common Commands

### View Current Deployment
```powershell
terraform show
```

### Get Dashboard URL Again
```powershell
terraform output app_runner_service_url
```

### Update Dashboard (after code changes)
```powershell
# Push changes to GitHub
git add .
git commit -m "Updated dashboard"
git push

# App Runner auto-deploys! (no terraform needed)
# Wait ~5 minutes for new version
```

### Change Password
```powershell
# Edit terraform.tfvars
notepad terraform.tfvars

# Apply changes
terraform apply
```

### Destroy Everything (cleanup)
```powershell
terraform destroy  # Type 'yes' to confirm
```

---

## 🐛 Troubleshooting

### **Issue: Terraform init fails**
**Solution:**
```powershell
# Check AWS credentials
aws sts get-caller-identity

# If fails, reconfigure
aws configure
```

### **Issue: GitHub connection error**
**Solution:**
- Verify the connection ARN in `terraform.tfvars`
- Check connection status in AWS Console → App Runner → Connections

### **Issue: App Runner build fails**
**Solution:**
- Check build logs: AWS Console → App Runner → Your service → Logs
- Common causes:
  - Missing `requirements.txt`
  - CSV files not in `app/` folder
  - Wrong file paths

### **Issue: Dashboard shows "Incorrect password"**
**Solution:**
- Check `terraform.tfvars` for correct password
- Password is case-sensitive
- Default: `DemoPassword2026!`

### **Issue: CSV files not loading**
**Solution:**
- Verify all 10 CSV files are in `app/` folder:
  ```powershell
  ls "C:\Users\Jeremiah\Desktop\cr ai work\Bidding\dashboard_app\app\*.csv"
  ```
- Should show:
  - executive_summary.csv
  - bidding_processes.csv
  - bidding_kpis.csv
  - preconstruction_processes.csv
  - preconstruction_kpis.csv
  - construction_processes.csv
  - construction_kpis.csv
  - closeout_processes.csv
  - closeout_kpis.csv
  - procore-itemized-combined.csv

---

## 📊 Monitoring & Maintenance

### View App Logs
```powershell
# In AWS Console
AWS Console → App Runner → Your service → Logs

# Or via CLI
aws apprunner list-operations --service-arn <YOUR_SERVICE_ARN>
```

### Check Service Health
```powershell
# Visit health check endpoint
curl https://YOUR-APP-URL.awsapprunner.com/_stcore/health
```

### Update to New Version
```powershell
# Just push to GitHub!
git add .
git commit -m "Update"
git push

# App Runner auto-deploys in ~5 minutes
```

---

## 🔐 Security Best Practices

### ✅ Currently Implemented:
- Password authentication
- HTTPS (automatic with App Runner)
- Non-root container user
- Encrypted Terraform state
- IAM least-privilege roles

### 🔒 Optional Enhancements:
1. **Stronger Password:** Change in `terraform.tfvars`
2. **IP Whitelisting:** Add WAF rules (additional cost)
3. **MFA:** Implement via AWS Cognito (more complex)
4. **Private Deployment:** Use VPC connector (additional setup)

---

## 📞 Support

**Issues with this deployment?**
- Check the troubleshooting section above
- Review Terraform logs: `terraform show`
- Check AWS Console: App Runner service logs

**Need to modify the dashboard?**
- Edit files in `app/` folder
- Push to GitHub
- Auto-deploys!

---

## 🎓 Next Steps

### **For Insurance Dashboard:**
1. Repeat this process with `CR-Score_executive_summary_insurance_v2.py`
2. Create separate Terraform workspace or folder
3. Use different `app_name` in `terraform.tfvars`

### **For Production:**
1. Consider custom domain (Route53 + Certificate Manager)
2. Set up monitoring alerts (CloudWatch)
3. Implement proper user management (AWS Cognito)
4. Add CI/CD pipeline (GitHub Actions)

---

## 📄 File Checklist

Before deploying, verify these files exist:

- [ ] `app/streamlit_app.py`
- [ ] `app/requirements.txt`
- [ ] `app/Dockerfile`
- [ ] `app/*.csv` (10 files)
- [ ] `terraform/main.tf`
- [ ] `terraform/variables.tf`
- [ ] `terraform/iam.tf`
- [ ] `terraform/apprunner.tf`
- [ ] `terraform/outputs.tf`
- [ ] `terraform/terraform.tfvars` (created from `.example`)

---

**🎉 You're all set! Follow the steps above and your dashboard will be live in ~30 minutes.**
