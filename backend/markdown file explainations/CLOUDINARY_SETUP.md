# Cloudinary Integration Setup Guide

## Overview

STYLO now supports **Cloudinary** for cloud-based image storage! This eliminates the need for base64 image storage and provides professional image hosting with automatic optimization, transformations, and CDN delivery.

## Features

✅ **Automatic Image Upload** - User-uploaded images are automatically sent to Cloudinary  
✅ **Optimized Delivery** - Images served via Cloudinary CDN with automatic format conversion  
✅ **Smart Fallback** - If Cloudinary is not configured, falls back to base64 storage  
✅ **Image Deletion** - Automatically removes images from Cloudinary when items are deleted  
✅ **Status Endpoint** - Check Cloudinary configuration status via API  

---

## Setup Instructions

### 1. Create a Cloudinary Account

1. Go to [https://cloudinary.com](https://cloudinary.com)
2. Sign up for a **free account** (includes 25GB storage & 25GB bandwidth/month)
3. After signup, you'll be redirected to the **Dashboard**

### 2. Get Your Credentials

On the Cloudinary Dashboard, you'll see:

```
Cloud Name: your_cloud_name
API Key: 123456789012345
API Secret: abcdefghijklmnopqrstuvwxyz
```

### 3. Configure STYLO Backend

#### Option A: Using `.env` file (Recommended)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your Cloudinary credentials:
   ```env
   # Cloudinary Configuration
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=123456789012345
   CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz
   CLOUDINARY_FOLDER=stylo_wardrobe
   
   # Enable Cloudinary
   USE_CLOUDINARY=true
   ```

#### Option B: Using Environment Variables

Set environment variables directly (Linux/Mac):
```bash
export CLOUDINARY_CLOUD_NAME="your_cloud_name"
export CLOUDINARY_API_KEY="123456789012345"
export CLOUDINARY_API_SECRET="abcdefghijklmnopqrstuvwxyz"
export USE_CLOUDINARY="true"
```

Windows PowerShell:
```powershell
$env:CLOUDINARY_CLOUD_NAME="your_cloud_name"
$env:CLOUDINARY_API_KEY="123456789012345"
$env:CLOUDINARY_API_SECRET="abcdefghijklmnopqrstuvwxyz"
$env:USE_CLOUDINARY="true"
```

### 4. Install Dependencies

If you haven't already, install the updated requirements:

```bash
pip install -r requirements.txt
```

This will install:
- `cloudinary==1.36.0` - Cloudinary Python SDK
- `python-dotenv==1.0.0` - Environment variable management

### 5. Restart the Backend

Stop the current backend server (Ctrl+C) and restart:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Verification

### Check Configuration Status

You can verify Cloudinary is configured correctly by visiting:

```
GET http://localhost:8000/wardrobe/cloudinary-status
```

Expected response:
```json
{
  "enabled": true,
  "configured": true,
  "cloud_name": "your_cloud_name",
  "folder": "stylo_wardrobe"
}
```

### Test Image Upload

1. Open the frontend: http://localhost:3000
2. Navigate to **Wardrobe**
3. Click **Add Item**
4. Upload an image or take a photo
5. Fill in the details and click **Add Item**
6. The image will be uploaded to Cloudinary automatically

---

## How It Works

### Upload Flow

```
User uploads image
    ↓
Frontend converts to base64
    ↓
Sends to backend /wardrobe POST endpoint
    ↓
Backend receives base64 image
    ↓
IF Cloudinary is configured:
    ├─ Upload to Cloudinary
    ├─ Get Cloudinary URL
    └─ Store Cloudinary URL in database
ELSE:
    └─ Store base64 directly (fallback)
    ↓
Return item with image URL
```

### Image Organization

All uploaded images are stored in Cloudinary with:
- **Folder**: `stylo_wardrobe/` (configurable)
- **Tags**: Automatically tagged with `wardrobe`, item type, and category
- **Optimization**: Auto format conversion (WebP for supported browsers)
- **Quality**: Auto-optimized for web delivery

---

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CLOUDINARY_CLOUD_NAME` | Your Cloudinary cloud name | - | Yes |
| `CLOUDINARY_API_KEY` | Your Cloudinary API key | - | Yes |
| `CLOUDINARY_API_SECRET` | Your Cloudinary API secret | - | Yes |
| `CLOUDINARY_FOLDER` | Folder to store images | `stylo_wardrobe` | No |
| `USE_CLOUDINARY` | Enable/disable Cloudinary | `true` | No |
| `MAX_IMAGE_SIZE` | Max image size in bytes | `10485760` (10MB) | No |

### Disable Cloudinary

To temporarily disable Cloudinary and use base64 storage:

```env
USE_CLOUDINARY=false
```

---

## Cloudinary Dashboard

### View Uploaded Images

1. Login to [Cloudinary Console](https://console.cloudinary.com)
2. Go to **Media Library**
3. Navigate to `stylo_wardrobe/` folder
4. See all uploaded wardrobe images

### Image Management

From the Cloudinary dashboard you can:
- View all uploaded images
- Download originals
- See usage statistics
- Set up transformations
- Configure access controls

---

## Troubleshooting

### ❌ "Cloudinary not configured" error

**Solution**: Make sure you've set all three required environment variables:
```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### ❌ Images still stored as base64

**Solution**: Check that `USE_CLOUDINARY=true` is set in your `.env` file.

### ❌ Import errors after installation

**Solution**: Make sure you've installed the new dependencies:
```bash
pip install -r requirements.txt
```

### ❌ "Invalid credentials" error

**Solution**: Double-check your Cloudinary credentials from the dashboard. Make sure there are no extra spaces or quotes.

---

## API Reference

### New Endpoint: Cloudinary Status

```http
GET /wardrobe/cloudinary-status
```

**Response:**
```json
{
  "enabled": true,
  "configured": true,
  "cloud_name": "your_cloud_name",
  "folder": "stylo_wardrobe"
}
```

### Modified Endpoint: Create Wardrobe Item

```http
POST /wardrobe
```

**Request Body:**
```json
{
  "type": "T-Shirt",
  "color": "Navy Blue",
  "category": "top",
  "image_url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response:** (with Cloudinary enabled)
```json
{
  "id": 13,
  "type": "T-Shirt",
  "color": "Navy Blue",
  "category": "top",
  "image_url": "https://res.cloudinary.com/your_cloud/image/upload/v1234567890/stylo_wardrobe/abc123.jpg",
  "cloudinary_id": "stylo_wardrobe/abc123"
}
```

---

## Cost & Limits

### Free Tier Includes:
- ✅ **25 GB** storage
- ✅ **25 GB** monthly bandwidth
- ✅ **25,000** monthly transformations
- ✅ **10,000** monthly image/video requests
- ✅ Unlimited cloud names

This is more than enough for development and small-scale production use!

### Upgrade Options:
If you need more, Cloudinary offers paid plans starting at $89/month with increased limits.

---

## Security Notes

⚠️ **Never commit your `.env` file to Git!**

The `.env` file is already in `.gitignore`, but double-check:

```bash
# Make sure .env is gitignored
echo ".env" >> .gitignore
```

⚠️ **Keep your API secret safe**

Your `CLOUDINARY_API_SECRET` is sensitive - treat it like a password!

---

## Migration Guide

If you already have items with base64 images and want to migrate them to Cloudinary:

1. Enable Cloudinary configuration
2. Delete old items
3. Re-add them - they'll automatically upload to Cloudinary
4. Or create a migration script (future enhancement)

---

## Next Steps

After setting up Cloudinary:

1. ✅ Test image upload through the UI
2. ✅ Check Cloudinary Media Library
3. ✅ Monitor your usage in the Cloudinary dashboard
4. ✅ Configure image transformations if needed
5. ✅ Set up production credentials when deploying

---

## Support

- **Cloudinary Docs**: https://cloudinary.com/documentation
- **STYLO Issues**: Create an issue on GitHub
- **Cloudinary Support**: support@cloudinary.com

---

**Happy styling with STYLO! 🎨👔**
