# 🚀 Quick Deploy to Streamlit Cloud

## Easiest Way (2 minutes):

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repo
   - **Main file path:** `ui/app.py`
   - Click "Deploy"

3. **That's it!** Your app will be live at `https://YOUR_APP.streamlit.app`

---

## ⚠️ Important Notes:

### Database File
The app needs a database file. Options:

**Option A: Include a sample database**
- Copy your `data/qs.duckdb` to the repo (may be large)
- Or create an empty one for demo

**Option B: Initialize on first run**
- Modify the app to auto-initialize if DB doesn't exist
- Users can populate data via the UI

**Option C: Use external storage**
- Store DB on S3/Cloud storage
- Load on startup (requires AWS credentials)

### Environment Variables
Set these in Streamlit Cloud (Settings → Secrets):
```toml
[default]
DUCKDB_PATH = "data/qs.duckdb"
```

---

## Alternative: Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub
4. Select your repo
5. Set environment variables
6. Deploy!

Railway will automatically use the `Procfile` to run your app.

---

## Need Help?

Check `DEPLOY.md` for detailed instructions for all platforms.

