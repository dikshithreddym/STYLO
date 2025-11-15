# 🚀 Render Deployment Checklist for STYLO v2

## ✅ Pre-Deployment Setup

### 1. Backend Code Ready
- [x] v2 suggestions endpoint at `/v2/suggestions`
- [x] Gemini image descriptions integrated
- [x] Recategorize endpoint at `/wardrobe/recategorize`
- [x] SQLite migration compatible with PostgreSQL
- [x] All dependencies in `requirements.txt`

### 2. Frontend Updated
- [x] Using `/v2/suggestions` endpoint
- [x] V2 response schema implemented
- [x] Intent display added

---

## 🔧 Render Backend Deployment

### Step 1: Push to GitHub
```bash
cd c:\Users\diksh\Desktop\Stylo_MVP
git add .
git commit -m "Add v2 intelligent suggestions with Gemini descriptions"
git push origin main
```

### Step 2: Environment Variables on Render

Go to Render Dashboard → Your Web Service → Environment

**Required Variables:**
```bash
# Database
DATABASE_URL=<your-postgres-internal-url>

# Cloudinary (Image Storage)
CLOUDINARY_CLOUD_NAME=dl4q2j9or
CLOUDINARY_API_KEY=984558728988178
CLOUDINARY_API_SECRET=v-YwhH7A_0kJiIRQbHmStlNuLvk
CLOUDINARY_FOLDER=stylo_wardrobe
USE_CLOUDINARY=true

# Google Gemini AI (Image Analysis)
GEMINI_API_KEY=AIzaSyBNWzfMrfbNTW4kVn7mryCDCz4OyrXNaOc

# App Settings
ENVIRONMENT=production
FRONTEND_URL=https://your-vercel-app.vercel.app
CORS_ORIGINS=https://your-vercel-app.vercel.app

# Python Version
PYTHON_VERSION=3.11.9
```

⚠️ **IMPORTANT**: Add the `GEMINI_API_KEY` environment variable - this enables AI image descriptions!

### Step 3: Deploy Backend
1. Render will auto-deploy when you push to `main`
2. Or manually: Dashboard → Deploy → **"Deploy latest commit"**
3. Wait 5-10 minutes for build to complete

### Step 4: Run Post-Deployment Setup

Once deployed, run these commands to set up your production wardrobe:

**Option A: Via Render Shell**
```bash
# SSH into Render service
render ssh stylo-backend

# Sync items from Cloudinary
curl -X POST https://your-backend.onrender.com/wardrobe/sync-cloudinary

# Backfill Gemini descriptions
curl -X POST https://your-backend.onrender.com/admin/backfill-descriptions

# Re-categorize based on descriptions
curl -X POST https://your-backend.onrender.com/wardrobe/recategorize
```

**Option B: Via Local Requests**
```powershell
# Replace with your actual Render backend URL
$baseUrl = "https://stylo-backend-xxxx.onrender.com"

# Sync from Cloudinary
Invoke-RestMethod -Uri "$baseUrl/wardrobe/sync-cloudinary" -Method POST

# Backfill descriptions (may take 2-3 minutes for 31 items)
Invoke-RestMethod -Uri "$baseUrl/admin/backfill-descriptions" -Method POST

# Recategorize
Invoke-RestMethod -Uri "$baseUrl/wardrobe/recategorize" -Method POST
```

---

## 🌐 Frontend Deployment to Vercel

### Step 1: Update Environment Variables
Vercel Dashboard → Your Project → Settings → Environment Variables

```bash
NEXT_PUBLIC_API_URL=https://stylo-backend-xxxx.onrender.com
```
(Use your actual Render backend URL)

### Step 2: Deploy
```bash
# Frontend auto-deploys when you push to main
git push origin main

# Or trigger manual deployment from Vercel Dashboard
```

---

## 🧪 Testing Production Deployment

### Test Backend Endpoints
```bash
# Replace with your Render URL
$url = "https://stylo-backend-xxxx.onrender.com"

# Health check
Invoke-RestMethod "$url/health"
# Expected: {"status": "ok"}

# Check wardrobe items
Invoke-RestMethod "$url/wardrobe?page=1&page_size=5"
# Expected: Array of 5 items with Gemini descriptions

# Test v2 suggestions
$body = @{text = "Business meeting"; limit = 2} | ConvertTo-Json
Invoke-RestMethod -Uri "$url/v2/suggestions" -Method POST -ContentType 'application/json' -Body $body
# Expected: {"intent": "business", "outfits": [...]}
```

### Test Frontend
1. Visit your Vercel URL: `https://stylo-xxxx.vercel.app`
2. Go to `/suggest` page
3. Enter prompt: "Professional business meeting"
4. Click "Get AI Suggestions"
5. Should see outfits with intent badge showing "business"

---

## 📊 Verify Gemini Integration

### Check if descriptions are populated:
```bash
curl https://your-backend.onrender.com/wardrobe/20
```

Should return item with detailed `image_description` like:
```json
{
  "id": 20,
  "type": "A4Dmqhhcocmbzsknhmfr",
  "category": "footwear",
  "image_description": "These are a pair of navy blue and white PUMA slide sandals, prominently branded..."
}
```

---

## ⚠️ Important Notes

### Cold Start (Render Free Tier)
- First request after 15 min inactivity takes ~30-60 seconds
- Backfill endpoint (`/admin/backfill-descriptions`) may timeout on first cold start
- Solution: Call health endpoint first to warm up, then retry backfill

### Gemini API Quotas
- Free tier: 60 requests/minute
- Your 31 items = 31 requests (under limit)
- Monitor usage: https://aistudio.google.com/app/apikey

### Database Migration
- SQLAlchemy automatically creates tables on first startup
- Migration script runs on startup to add `image_description` column
- Safe to run multiple times (idempotent)

---

## 🐛 Troubleshooting

### "Method Not Allowed" on `/wardrobe/recategorize`
**Cause**: Render hasn't reloaded with new code
**Fix**: Trigger manual redeploy from Render Dashboard

### Gemini descriptions not generated
**Check**:
1. `GEMINI_API_KEY` is set in Render environment
2. Cloudinary images are accessible (test image URL in browser)
3. Check logs: Render Dashboard → Logs tab

**Fix**: Re-run backfill:
```bash
curl -X POST https://your-backend.onrender.com/admin/backfill-descriptions
```

### v2 suggestions return empty outfits
**Check**:
1. Items are properly categorized: `/wardrobe?page=1&page_size=50`
2. Categories should be: top, bottom, footwear, layer, accessories
3. Run recategorize: `POST /wardrobe/recategorize`

### Frontend shows 400 error
**Cause**: Not enough items with required categories (tops, bottoms, footwear)
**Fix**: Add more clothing items to Cloudinary and re-sync

---

## 📝 Optional: Can You Delete `suggestions.py`?

### Answer: **Keep it for now (recommended)**

**Reasons to keep:**
- ✅ Provides fallback if v2 has issues
- ✅ Different use case (rules-based vs AI-powered)
- ✅ Minimal code size (~1000 lines)
- ✅ No performance impact (not called unless explicitly requested)

**If you want to delete:**
1. Remove from `app/main.py`:
   ```python
   # Delete this line:
   from app.routers import suggestions
   app.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
   ```
2. Delete file: `backend/app/routers/suggestions.py`
3. Frontend already uses v2, so no impact

**My recommendation**: Keep both endpoints active for 1-2 weeks, then remove v1 if v2 works perfectly.

---

## ✅ Deployment Complete!

Once all steps are done:
- ✅ Backend running on Render with PostgreSQL
- ✅ Frontend deployed on Vercel
- ✅ 31 items synced from Cloudinary
- ✅ Gemini descriptions generated
- ✅ Items properly categorized (tops, bottoms, footwear, layers, accessories)
- ✅ v2 intelligent suggestions working with semantic matching
- ✅ Intent detection (business, party, workout, casual, etc.)
- ✅ Color harmony and context-aware outfit assembly

**Your STYLO app is production-ready! 🎉**
