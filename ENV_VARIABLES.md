# Environment Variables Reference

## 🔧 Backend (Render)

### Required
```bash
DATABASE_URL=postgresql://user:password@host:5432/database
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
FRONTEND_URL=https://your-app.vercel.app
```

### Optional
```bash
CLOUDINARY_FOLDER=stylo_wardrobe
USE_CLOUDINARY=true
MAX_IMAGE_SIZE=10485760
ENVIRONMENT=production
```

---

## 🌐 Frontend (Vercel)

### Required
```bash
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

---

## 📝 Notes

1. **DATABASE_URL**: 
   - Automatically provided by Render PostgreSQL
   - Copy from Database → Connect → Internal Database URL

2. **FRONTEND_URL**:
   - Get from Vercel after deployment
   - Format: `https://your-app.vercel.app`

3. **NEXT_PUBLIC_API_URL**:
   - Must start with `NEXT_PUBLIC_` to be accessible in browser
   - Get from Render after backend deployment

4. **Cloudinary Credentials**:
   - From Cloudinary Dashboard
   - Same values as in `backend/.env`
