# Dashboard App

This repository contains the Streamlit dashboard application for the Construction Risk AI platform.

🚀 **CI/CD Pipeline Active** - Auto-deploys to dev on every push to main!

## 🏗️ Architecture

- **Frontend**: Streamlit Python web application
- **Authentication**: AWS Cognito integration
- **Deployment**: AWS ECS Fargate with GitHub Actions CI/CD
- **Container Registry**: AWS ECR

## 🚀 Deployment

### Environments
- **Dev**: Auto-deploys on every push to `main`
- **Production**: Manual promotion via GitHub Actions

### URLs
- **Dev**: https://construction-risk-ai-dev.crai.ai/
- **Production**: https://construction-risk-ai.crai.ai/

## 📋 Setup

See [DEPLOYMENT_SETUP.md](DEPLOYMENT_SETUP.md) for complete CI/CD setup instructions.

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements_streamlit.txt

# Run locally
streamlit run PROD_streamlit_app_UPDATED.py
```

## 📁 File Structure

- `Dockerfile` - Container configuration
- `PROD_streamlit_app_UPDATED.py` - Main application (latest version)
- `cognito_auth.py` / `PROD_cognito_auth.py` - Authentication modules
- `requirements_streamlit.txt` - Python dependencies
- `.github/workflows/deploy.yml` - CI/CD pipeline
- `scripts/` - Deployment helper scripts
- `task-definition-*.json` - ECS task configurations

## 🔄 CI/CD Workflow

1. **Push to main** → Auto-deploy to dev environment
2. **Manual promotion** → Deploy to production via GitHub Actions
3. **Rollback** → Use `scripts/rollback.sh` if needed

See [CI_CD_SUMMARY.md](CI_CD_SUMMARY.md) for detailed workflow documentation.