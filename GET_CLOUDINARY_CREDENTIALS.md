# 🔑 Getting Your Cloudinary Credentials

## Step-by-Step Guide

### 1. Sign Up for Cloudinary

1. Go to: **https://cloudinary.com/users/register/free**
2. Fill in the form:
   - Email address
   - Password
   - Choose a cloud name (this will be your `CLOUDINARY_CLOUD_NAME`)
3. Click **"Create Account"**

### 2. Email Verification

1. Check your email inbox
2. Click the verification link
3. You'll be redirected to your dashboard

### 3. Get Your Credentials

Once logged in, you'll see your **Dashboard** with:

```
┌─────────────────────────────────────────┐
│ Account Details                          │
├─────────────────────────────────────────┤
│ Cloud name:    your_cloud_name          │
│ API Key:       123456789012345           │
│ API Secret:    ●●●●●●●●●●●●●●●● (Show)  │
└─────────────────────────────────────────┘
```

**Click "Show" next to API Secret to reveal it**

### 4. Copy to .env File

Open `backend/.env` and add:

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=your_actual_secret_here
USE_CLOUDINARY=true
```

### 5. Restart Backend

```bash
# Stop current backend (Ctrl+C)
# Then restart:
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Verify

Visit: http://localhost:8000/wardrobe/cloudinary-status

Should show:
```json
{
  "enabled": true,
  "configured": true,
  "cloud_name": "your_cloud_name",
  "folder": "stylo_wardrobe"
}
```

---

## 🖼️ Visual Guide

### Dashboard Location

After login, you'll immediately see:

```
┌────────────────────────────────────────────────────────┐
│  Cloudinary Console                                    │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Welcome to Cloudinary!                                │
│                                                        │
│  Account Details                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ Cloud name:  my_stylo_cloud                   │    │
│  │ API Key:     123456789012345                  │    │
│  │ API Secret:  abc123def456 (Show/Hide)        │    │
│  │ Environment: CLOUDINARY_URL=cloudinary://... │    │
│  └──────────────────────────────────────────────┘    │
│                                                        │
│  Usage This Month                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ Storage:    0.5 GB / 25 GB                    │    │
│  │ Bandwidth:  1.2 GB / 25 GB                    │    │
│  └──────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Quick Checklist

- [ ] Created Cloudinary account
- [ ] Verified email
- [ ] Copied cloud name
- [ ] Copied API key
- [ ] Revealed and copied API secret
- [ ] Pasted all three into `backend/.env`
- [ ] Set `USE_CLOUDINARY=true`
- [ ] Restarted backend
- [ ] Verified status endpoint shows "configured": true
- [ ] Tested image upload

---

## ⚠️ Common Mistakes

### ❌ Wrong: Copying the Environment URL
Don't copy `CLOUDINARY_URL=cloudinary://key:secret@cloud`

### ✅ Correct: Copy individual values
```env
CLOUDINARY_CLOUD_NAME=my_stylo_cloud
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abc123def456
```

### ❌ Wrong: Including quotes
```env
CLOUDINARY_CLOUD_NAME="my_stylo_cloud"  # Don't do this
```

### ✅ Correct: No quotes
```env
CLOUDINARY_CLOUD_NAME=my_stylo_cloud
```

### ❌ Wrong: Forgetting to restart
Just saving `.env` isn't enough - must restart backend!

### ✅ Correct: Always restart after changing .env
```bash
# Stop with Ctrl+C
# Start again
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔒 Security Tips

1. **Never commit `.env` file**
   - Already in `.gitignore`
   - Double-check before committing

2. **Don't share your API Secret**
   - Treat it like a password
   - Regenerate if exposed

3. **Use environment variables in production**
   - Don't hardcode credentials
   - Use your hosting platform's secret management

4. **Rotate keys if needed**
   - Can regenerate from Cloudinary dashboard
   - Settings → Security → API Keys

---

## 🎯 That's It!

You're done! Your STYLO app is now using Cloudinary for image storage.

**Test it:**
1. Go to http://localhost:3000
2. Click "Wardrobe"
3. Add an item with an image
4. Check your Cloudinary Media Library - the image is there!

**View your images:**
1. Login to Cloudinary
2. Go to "Media Library"
3. Navigate to `stylo_wardrobe` folder
4. See all uploaded images

---

## 📞 Need Help?

- **Can't find dashboard?** Go to: https://console.cloudinary.com
- **Forgot password?** Use password reset
- **Need more details?** See `backend/CLOUDINARY_SETUP.md`
- **API not working?** Check status endpoint first

---

**Free tier includes: 25GB storage + 25GB bandwidth/month**

That's enough for thousands of wardrobe images! 🎉
