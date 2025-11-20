# STYLO Deployment Guide

## 🚀 Quick Overview

- **Frontend**: Vercel (Static hosting for Next.js)
- **Backend**: Render (Python web service)
- **Database**: Render PostgreSQL (Free tier)
- **Images**: Cloudinary (Cloud storage)

**✅ No file storage on backend server - Everything uses Cloudinary + PostgreSQL**

---

## 📦 Part 1: Deploy Backend to Render

### Step 1: Create Render Account
1. Go to [https://render.com](https://render.com)
2. Sign up with GitHub (recommended for auto-deployment)

### Step 2: Create PostgreSQL Database
1. From Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `stylo-database`
   - **Database**: `stylo_db`
   - **User**: `stylo_user`
   - **Region**: Choose closest to you
   - **Plan**: **Free** (0 GB storage, sufficient for development)
3. Click **"Create Database"**
4. **Copy the Internal Database URL** (starts with `postgresql://`)
   - You'll need this for the web service

### Step 3: Deploy Backend Web Service
1. From Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository `STYLO`
3. Configure:
   - **Name**: `stylo-backend` (or your preferred name)
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: **Free** (512 MB RAM, spins down after inactivity)

4. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   DATABASE_URL = <paste your PostgreSQL Internal URL>
   CLOUDINARY_CLOUD_NAME = dl4q2j9or
   CLOUDINARY_API_KEY = 984558728988178
   CLOUDINARY_API_SECRET = v-YwhH7A_0kJiIRQbHmStlNuLvk
   CLOUDINARY_FOLDER = stylo_wardrobe
   USE_CLOUDINARY = true
   ENVIRONMENT = production
   FRONTEND_URL = https://your-vercel-app.vercel.app
   ```
   
   **Note**: Update `FRONTEND_URL` after deploying frontend in Step 6

5. Click **"Create Web Service"**
6. Wait 5-10 minutes for deployment
7. **Copy your backend URL**: `https://stylo-backend-xxxx.onrender.com`

### Step 4: Verify Backend
Visit your backend URL:
```
https://stylo-backend-xxxx.onrender.com/health
```

Should return:
```json
{"status": "ok"}
```

Check Cloudinary status:
```
https://stylo-backend-xxxx.onrender.com/wardrobe/cloudinary-status
```

Should return:
```json
{
  "enabled": true,
  "configured": true,
  "cloud_name": "dl4q2j9or",
  "folder": "stylo_wardrobe"
}
```

---

## 🌐 Part 2: Deploy Frontend to Vercel

### Step 1: Create Vercel Account
1. Go to [https://vercel.com](https://vercel.com)
2. Sign up with GitHub

### Step 2: Import Project
1. Click **"Add New..."** → **"Project"**
2. Import your `STYLO` repository
3. Configure:
   - **Framework Preset**: **Next.js** (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

### Step 3: Set Environment Variables
Under **"Environment Variables"**:
```
NEXT_PUBLIC_API_URL = https://stylo-backend-xxxx.onrender.com
```
(Use your Render backend URL from Part 1, Step 3)

### Step 4: Deploy
1. Click **"Deploy"**
2. Wait 2-3 minutes
3. **Copy your frontend URL**: `https://stylo-xxxx.vercel.app`

### Step 5: Update Backend CORS
1. Go back to Render Dashboard → Your Web Service
2. Go to **"Environment"** tab
3. Update `FRONTEND_URL`:
   ```
   FRONTEND_URL = https://stylo-xxxx.vercel.app
   ```
4. Click **"Save Changes"** (triggers auto-redeploy)

### Step 6: Test Production App
Visit your Vercel URL:
```
https://stylo-xxxx.vercel.app
```

✅ Should load the STYLO app connected to production backend!

---

## 🔄 Auto-Deployment Setup

### Render (Backend)
✅ **Already configured!** Every push to `main` branch auto-deploys.

To disable:
- Render Dashboard → Web Service → Settings → **"Auto-Deploy: Off"**

### Vercel (Frontend)
✅ **Already configured!** Every push auto-deploys.

Production branch: `main`
Preview branches: All other branches get preview URLs

To configure:
- Vercel Dashboard → Project Settings → Git → Branch settings

---

## 🗄️ Database Management

### View Database
1. Render Dashboard → PostgreSQL database → **"Connect"**
2. Use provided connection details with any PostgreSQL client (e.g., pgAdmin, DBeaver)

### Run Migrations
Database tables are auto-created on first backend startup via SQLAlchemy:
```python
# In main.py
Base.metadata.create_all(bind=engine)
```

### Backup Database
1. Render Dashboard → Database → **"Backups"** tab
2. Free tier: Manual backups only
3. Click **"Create Backup"**

### Reset Database
**⚠️ WARNING: Deletes all data!**
```bash
# Connect to Render Shell
render ssh <your-service-name>

# Drop and recreate tables
python -c "from app.database import engine, Base; from app.models import *; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

---

## 📊 Monitoring & Logs

### Backend Logs (Render)
1. Render Dashboard → Web Service → **"Logs"** tab
2. Real-time streaming logs
3. Filter by severity: Info, Warning, Error

### Frontend Logs (Vercel)
1. Vercel Dashboard → Project → **"Logs"** tab
2. View:
   - Build logs
   - Function logs
   - Edge logs

### Database Logs (Render)
1. Render Dashboard → PostgreSQL → **"Logs"** tab
2. Connection logs
3. Query performance

---

## ⚠️ Important Notes

### Render Free Tier Limitations
- ✅ **No file storage** - We use Cloudinary instead
- ⚠️ **Spins down after 15 min inactivity** - First request after sleep takes ~30-60 seconds
- ✅ **750 hours/month free** (enough for 1 service running 24/7)
- ✅ **PostgreSQL 1 GB** storage free

### Vercel Free Tier Limitations
- ✅ **100 GB bandwidth/month**
- ✅ Unlimited projects
- ✅ Automatic HTTPS
- ✅ Global CDN

### Cloudinary Free Tier
- ✅ **25 GB storage**
- ✅ **25 GB bandwidth/month**
- ✅ 25,000 transformations/month

### Cold Start Mitigation
Render spins down free-tier services after inactivity. To keep it warm:

**Option 1**: Use UptimeRobot (free service)
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add monitor: `https://stylo-backend-xxxx.onrender.com/health`
3. Interval: 5 minutes
4. Keeps backend alive 24/7

**Option 2**: Upgrade to Render Starter plan ($7/month)
- No spin-down
- Better performance

---

## 🔐 Security Checklist

### ✅ Backend
- [x] Cloudinary credentials in environment variables (not in code)
- [x] Database URL not committed to Git
- [x] CORS restricted to frontend URL
- [x] HTTPS enforced by Render

### ✅ Frontend
- [x] API URL in environment variable
- [x] No secrets in client-side code
- [x] HTTPS enforced by Vercel

### ✅ Database
- [x] PostgreSQL with SSL
- [x] Private network (Internal URL)
- [x] No public access

---

## 🐛 Troubleshooting

### Backend not accessible
```bash
# Check logs
render logs <service-name>

# Check environment variables
render env list <service-name>

# Restart service
render restart <service-name>
```

### Database connection failed
- Verify `DATABASE_URL` in Render environment variables
- Check database is running (Render Dashboard)
- Ensure backend and database are in same region

### Frontend 404 errors
- Check `NEXT_PUBLIC_API_URL` in Vercel environment variables
- Verify backend is accessible from browser
- Check browser console for CORS errors

### Images not uploading
- Verify Cloudinary credentials in Render environment
- Check Cloudinary dashboard for quota limits
- Test `/wardrobe/cloudinary-test` endpoint

---

## 🔄 Updating the App

### Update Backend
```bash
git add .
git commit -m "Backend update"
git push origin main
```
→ Render auto-deploys in ~5 minutes

### Update Frontend
```bash
git add .
git commit -m "Frontend update"
git push origin main
```
→ Vercel auto-deploys in ~2 minutes

### Update Dependencies
**Backend**:
1. Update `backend/requirements.txt`
2. Push to GitHub
3. Render rebuilds automatically

**Frontend**:
1. Update `frontend/package.json`
2. Push to GitHub
3. Vercel rebuilds automatically

---

## 📞 Support

### Render
- Docs: https://render.com/docs
- Status: https://status.render.com

### Vercel
- Docs: https://vercel.com/docs
- Support: [vercel.com/support](https://vercel.com/support)

### Cloudinary
- Docs: https://cloudinary.com/documentation
- Support: support@cloudinary.com

---

## ✅ Deployment Complete!

Your STYLO app is now live:
- 🌐 **Frontend**: `https://stylo-xxxx.vercel.app`
- 🔧 **Backend**: `https://stylo-backend-xxxx.onrender.com`
- 🗄️ **Database**: PostgreSQL on Render
- ☁️ **Images**: Cloudinary CDN

**No local file storage - Everything is in the cloud!** 🎉
