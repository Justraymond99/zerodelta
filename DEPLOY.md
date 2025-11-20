# Deployment Guide

## 🚀 Best Options for Deploying Streamlit

Streamlit requires a **persistent Python server**, so Vercel (which is serverless) won't work. Here are the best alternatives:

---

## Option 1: Streamlit Cloud ⭐ (Easiest - FREE)

**Best for**: Quick deployment, zero config

### Steps:
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repo and branch
6. Set main file: `ui/app.py`
7. Click "Deploy"

### Pros:
- ✅ Completely free
- ✅ Zero configuration
- ✅ Automatic deployments on git push
- ✅ HTTPS included
- ✅ Handles dependencies automatically

### Cons:
- ❌ Limited to Streamlit apps only
- ❌ Shared resources (may be slower during peak)

---

## Option 2: Railway 🚂 (Recommended)

**Best for**: Full control, good performance

### Setup:

1. **Create `Procfile`:**
```
web: streamlit run ui/app.py --server.port=$PORT --server.address=0.0.0.0
```

2. **Create `runtime.txt`:**
```
python-3.11.0
```

3. **Deploy:**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Select your repo
   - Railway will auto-detect Python and install dependencies
   - Set environment variables in Railway dashboard

### Pros:
- ✅ $5/month free credits
- ✅ Full control
- ✅ Can run multiple services (API, daemon, etc.)
- ✅ Good performance
- ✅ Easy scaling

---

## Option 3: Render 🌐

**Best for**: Free tier, Docker support

### Setup:

1. **Create `render.yaml`:**
```yaml
services:
  - type: web
    name: trading-dashboard
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run ui/app.py --server.port=$PORT --server.address=0.0.0.0
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

2. **Deploy:**
   - Go to [render.com](https://render.com)
   - Sign in with GitHub
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml`

### Pros:
- ✅ Free tier (spins down after inactivity)
- ✅ Docker support
- ✅ Auto-deployments

### Cons:
- ❌ Free tier has cold starts
- ❌ Limited free resources

---

## Option 4: Docker + Any Platform

**Best for**: Maximum flexibility

### Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Run streamlit
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Deploy anywhere:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform
- Fly.io

---

## Environment Variables

Make sure to set these in your deployment platform:

```bash
# Database
DUCKDB_PATH=data/qs.duckdb

# Optional: API keys if using
POLYGON_API_KEY=your_key
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
```

---

## Quick Deploy Script

For local testing before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DUCKDB_PATH=data/qs.duckdb

# Run locally
streamlit run ui/app.py
```

---

## Recommended: Streamlit Cloud

**Fastest way to get live:**
1. Push code to GitHub
2. Go to share.streamlit.io
3. Deploy in 2 minutes

That's it! 🎉

