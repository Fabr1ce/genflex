# GenFlex Creative Storyteller - Deployment Guide

## Overview
This guide provides step-by-step instructions to deploy the GenFlex Creative Storyteller application to Google Cloud Platform for the Google AI Hackathon.

## Prerequisites
- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Terraform v1.0+ installed
- Docker installed (for container builds)

## Quick Deployment

### 1. Set up Google Cloud Project
```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Authenticate and Configure
```bash
# Authenticate with Google Cloud
gcloud auth login

# Set the project and region
gcloud config set project $PROJECT_ID
gcloud config set compute/region us-central1
```

### 3. Build and Push Docker Image
```bash
# Build the container
docker build -t gcr.io/$PROJECT_ID/genflex-storyteller:latest .

# Push to Google Container Registry
gcloud auth configure-docker
docker push gcr.io/$PROJECT_ID/genflex-storyteller:latest
```

### 4. Deploy with Terraform
```bash
cd infrastructure

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -var="project_id=$PROJECT_ID"

# Apply the deployment
terraform apply -var="project_id=$PROJECT_ID"
```

### 5. Get the Service URL
After deployment, Terraform will output the Cloud Run service URL:
```
cloud_run_url = "https://genflex-storyteller-xyz-uc.a.run.app"
```

## Manual Deployment (Alternative)

If you prefer manual deployment without Terraform:

### Deploy to Cloud Run
```bash
gcloud run deploy genflex-storyteller \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GEMINI_MODEL=gemini-2.5-flash"
```

## Environment Variables

The application uses the following environment variables:

- `GEMINI_MODEL`: AI model to use (default: `gemini-2.5-flash`)
- `GOOGLE_CLOUD_PROJECT`: GCP project ID (auto-detected)
- `GOOGLE_CLOUD_LOCATION`: GCP region (default: `global`)

## Testing the Deployment

### 1. Access the Web Interface
Open the Cloud Run URL in your browser to access the web interface.

### 2. Test the API
```bash
# Test the story generation endpoint
curl -X POST "https://your-service-url/story" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me a short story about a robot who falls in love"}'
```

### 3. Verify Multimodal Output
The API should return interleaved content with:
- Text narratives
- Image generation prompts
- Audio narration descriptions
- Video segment descriptions

## Architecture Overview

### Components
- **FastAPI Web Server**: Handles HTTP requests and serves the web interface
- **Google ADK Agent**: Core AI agent with multimodal storytelling capabilities
- **Gemini 2.5-flash**: Primary AI model for content generation
- **Cloud Run**: Serverless container platform
- **Memorystore (Redis)**: Session management and caching
- **Vertex AI**: AI platform services

### Security Features
- Prompt injection protection
- Restricted to storytelling only
- Authentication via Google Cloud IAM

## Troubleshooting

### Common Issues

**Authentication Errors:**
```bash
gcloud auth login
gcloud auth application-default login
```

**API Not Enabled:**
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable run.googleapis.com
```

**Container Build Issues:**
- Ensure Docker is running
- Check that you're authenticated with gcr.io

**Terraform State Issues:**
```bash
terraform refresh
terraform plan
```

## Performance Optimization

- The application uses async processing for better performance
- Memorystore provides fast session caching
- Cloud Run auto-scales based on demand

## Cost Estimation

- **Cloud Run**: ~$0.10/hour for basic usage
- **Vertex AI**: Pay-per-request for Gemini API calls
- **Memorystore**: ~$0.02/hour for basic Redis instance

## Hackathon Submission Checklist

- [ ] Application deployed to Google Cloud
- [ ] Web interface accessible
- [ ] Multimodal storytelling working
- [ ] API endpoints functional
- [ ] Authentication configured
- [ ] Infrastructure documented
- [ ] Demo video prepared
- [ ] Architecture diagram created

## Support

For issues during deployment, check:
1. Google Cloud Console logs
2. Terraform output for error messages
3. Application logs in Cloud Run
4. Network connectivity to Google APIs