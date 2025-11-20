# 🚀 Quick Deploy Commands

## Step 1: Push to GitHub
```bash
cd c:\Users\diksh\Desktop\Stylo_MVP
git add .
git commit -m "Deploy v2 with Gemini AI + PostgreSQL ready"
git push origin main
```

## Step 2: Wait for Render Build (8-12 minutes)
Watch at: https://dashboard.render.com

## Step 3: Initialize Production Database

Replace `YOUR_BACKEND_URL` with your actual Render URL (e.g., `https://stylo-backend-abc.onrender.com`)

### PowerShell Commands:
```powershell
# Set your backend URL
$url = "https://YOUR_BACKEND_URL"

# 1. Health check (warms up cold start)
Invoke-RestMethod -Uri "$url/health"

# 2. Sync from Cloudinary (31 items)
Invoke-RestMethod -Uri "$url/wardrobe/sync-cloudinary" -Method POST

# 3. Generate Gemini descriptions (takes 2-3 minutes)
Invoke-RestMethod -Uri "$url/admin/backfill-descriptions" -Method POST

# 4. Recategorize items
Invoke-RestMethod -Uri "$url/wardrobe/recategorize" -Method POST

# 5. Verify categories
Invoke-RestMethod -Uri "$url/wardrobe?page=1&page_size=5"

# 6. Test v2 suggestions
$body = @{text = "Business meeting"; limit = 2} | ConvertTo-Json
Invoke-RestMethod -Uri "$url/v2/suggestions" -Method POST -ContentType 'application/json' -Body $body
```

### Bash/cURL Commands:
```bash
# Set your backend URL
URL="https://YOUR_BACKEND_URL"

# 1. Health check
curl $URL/health

# 2. Sync from Cloudinary
curl -X POST $URL/wardrobe/sync-cloudinary

# 3. Generate Gemini descriptions
curl -X POST $URL/admin/backfill-descriptions

# 4. Recategorize items
curl -X POST $URL/wardrobe/recategorize

# 5. Verify categories
curl "$URL/wardrobe?page=1&page_size=5"

# 6. Test v2 suggestions
curl -X POST $URL/v2/suggestions \
  -H "Content-Type: application/json" \
  -d '{"text": "Business meeting", "limit": 2}'
```

## Expected Output

### After sync-cloudinary:
```json
{"status": "ok", "created": 31, "folder": "stylo_wardrobe"}
```

### After backfill-descriptions:
```json
{"status": "success", "message": "Backfill completed successfully", "output": "..."}
```

### After recategorize:
```json
{"status": "ok", "updated": 25}
```

### After v2 suggestions test:
```json
{
  "intent": "business",
  "outfits": [
    {
      "top": {"id": 33, "name": "...", "category": "top"},
      "bottom": {"id": 34, "name": "...", "category": "bottom"},
      "footwear": {"id": 28, "name": "...", "category": "footwear"},
      "outerwear": {"id": 24, "name": "...", "category": "layer"},
      "accessories": {"id": 42, "name": "...", "category": "accessories"}
    }
  ]
}
```

## Troubleshooting

### Backfill times out?
```powershell
# Call health first to warm up
Invoke-RestMethod -Uri "$url/health"
Start-Sleep -Seconds 5
# Then retry backfill
Invoke-RestMethod -Uri "$url/admin/backfill-descriptions" -Method POST
```

### Empty outfits?
```powershell
# Ensure recategorize ran
Invoke-RestMethod -Uri "$url/wardrobe/recategorize" -Method POST
```

### Check logs:
Go to Render Dashboard → Your Service → Logs tab

---

## ✅ Done!

Once all commands complete successfully, your production database is ready with:
- 31 items synced from Cloudinary
- Gemini AI descriptions for all items
- Proper categories (tops, bottoms, footwear, layers, accessories)
- v2 intelligent suggestions working!

Next: Update Vercel environment variable `NEXT_PUBLIC_API_URL` with your Render backend URL
