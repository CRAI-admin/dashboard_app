# Dashboard App

A Streamlit-based dashboard application for construction project management.

## Project Structure

```
dashboard_app/
├── README.md
├── requirements.txt
├── Dockerfile
├── app/
│   ├── streamlit_app.py
│   └── cognito_auth.py
└── .gitignore
```

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run locally: `streamlit run app/streamlit_app.py`
3. Deploy with Docker: `docker build -t dashboard_app .`

## Deployment

This application is deployed on AWS ECS with CloudFront CDN.