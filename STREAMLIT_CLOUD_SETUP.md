# 🚀 Streamlit Cloud Deployment Guide

## Quick Setup Steps

### 1. **Deploy on Streamlit Cloud** (2 minutes)

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your **GitHub** account
3. Click **"New app"**
4. Configure:
   - **Repository**: `Justraymond99/zerodelta` (or select from list)
   - **Branch**: `main`
   - **Main file path**: `ui/app.py`
   - **App URL**: (choose your custom subdomain)
5. Click **"Deploy"**

### 2. **Set Secrets/Environment Variables** (Optional)

In Streamlit Cloud dashboard → Settings → Secrets, add:

```toml
[default]
DUCKDB_PATH = "data/qs.duckdb"

# Optional: Add if using external APIs
POLYGON_API_KEY = "your_key_here"
ALPACA_API_KEY = "your_key_here"
ALPACA_SECRET_KEY = "your_secret_here"
TWILIO_ACCOUNT_SID = "your_sid_here"
TWILIO_AUTH_TOKEN = "your_token_here"
TWILIO_FROM = "+1234567890"
TWILIO_ALLOWED_NUMBERS = "+1234567890,+0987654321"
```

### 3. **That's it!**

Your app will be live at: `https://YOUR-APP-NAME.streamlit.app`

## ⚠️ Important Notes

### Database File
- Streamlit Cloud will start with an empty database
- Users can use the "📥 Fetch Popular Tickers" button in the sidebar to load initial data
- The database file is ephemeral (resets on redeploy unless you persist it)

### First Time Setup
- On first load, click "📥 Fetch Popular Tickers" to populate the database
- This will fetch data for popular tickers (AAPL, MSFT, SPY, etc.)

### Auto-Deployments
- Every push to `main` branch automatically redeploys the app
- No manual deployment needed!

## Troubleshooting

If you see errors:
1. Check the logs in Streamlit Cloud dashboard
2. Make sure `requirements.txt` has all dependencies
3. Verify the main file path is `ui/app.py`
4. Check that all imports are working correctly

## Next Steps

After deployment:
1. Test the app at your Streamlit Cloud URL
2. Click "📥 Fetch Popular Tickers" to load data
3. Explore all the features!

