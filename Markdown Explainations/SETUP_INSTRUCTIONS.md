# STYLO MVP - Setup and Run Instructions

## Complete Setup Guide

### System Requirements
- Python 3.10 or higher
- Node.js 18 or higher  
- npm (comes with Node.js)
- Git (optional)

---

## Step-by-Step Setup

### BACKEND SETUP

1. **Open Terminal/PowerShell** and navigate to the backend folder:
```powershell
cd C:\Users\diksh\Desktop\Stylo_MVP\backend
```

2. **Create a Python virtual environment:**
```powershell
python -m venv venv
```

3. **Activate the virtual environment:**
```powershell
.\venv\Scripts\activate
```
You should see `(venv)` at the start of your terminal prompt.

4. **Install Python dependencies:**
```powershell
pip install -r requirements.txt
```

5. **Run the backend server:**
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

✅ Backend is now running! Keep this terminal open.

Test it by opening: http://localhost:8000/docs

---

### FRONTEND SETUP

1. **Open a NEW Terminal/PowerShell window** and navigate to the frontend folder:
```powershell
cd C:\Users\diksh\Desktop\Stylo_MVP\frontend
```

2. **Install Node.js dependencies:**
```powershell
npm install
```

This will take a few minutes as it downloads all packages.

3. **Create environment file:**
```powershell
Copy-Item .env.example .env.local
```

4. **Run the frontend development server:**
```powershell
npm run dev
```

You should see:
```
- Local:        http://localhost:3000
- ready started server on 0.0.0.0:3000
```

✅ Frontend is now running!

---

## Accessing the Application

1. **Open your web browser**
2. **Navigate to:** http://localhost:3000
3. **Explore the app:**
   - Landing page with features
   - Dashboard with statistics
   - Wardrobe page (fetches data from backend API)

---

## Troubleshooting

### Backend Issues

**Problem:** `uvicorn: command not found` or similar
**Solution:** Make sure virtual environment is activated (you should see `(venv)` in terminal)

**Problem:** Port 8000 already in use
**Solution:** Change port:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```
Then update frontend `.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8001`

### Frontend Issues

**Problem:** `npm: command not found`
**Solution:** Install Node.js from https://nodejs.org/

**Problem:** Port 3000 already in use
**Solution:** Next.js will automatically suggest port 3001. Press 'y' to use it.

**Problem:** "Failed to load wardrobe items"
**Solution:** Make sure the backend is running on port 8000

---

## Stopping the Servers

### Stop Backend:
- Press `Ctrl+C` in the backend terminal
- Deactivate virtual environment: `deactivate`

### Stop Frontend:
- Press `Ctrl+C` in the frontend terminal

---

## Restarting Later

### Backend:
```powershell
cd C:\Users\diksh\Desktop\Stylo_MVP\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend:
```powershell
cd C:\Users\diksh\Desktop\Stylo_MVP\frontend
npm run dev
```

---

## Project Structure Overview

```
Stylo_MVP/
├── backend/                  # FastAPI Backend (Port 8000)
│   ├── app/
│   │   ├── main.py          # Server entry point
│   │   ├── schemas.py       # Data models
│   │   └── routers/
│   │       └── wardrobe.py  # API endpoints
│   └── requirements.txt     # Python dependencies
│
└── frontend/                # Next.js Frontend (Port 3000)
    ├── src/
    │   ├── app/            # Pages
    │   ├── components/     # UI components
    │   └── lib/           # API client
    └── package.json       # Node dependencies
```

---

## Features Available in Phase 1

✅ **Landing Page** - Hero section with call-to-actions
✅ **Dashboard** - Overview with statistics  
✅ **Wardrobe** - View 10 sample clothing items
✅ **Responsive Design** - Works on mobile and desktop
✅ **API Integration** - Frontend fetches data from backend

---

## What's NOT Included (Yet)

❌ User login/signup
❌ Authentication
❌ Database (using dummy data)
❌ Adding/editing items
❌ User accounts

These will be added in future phases!

---

## Need Help?

1. Make sure both terminals are running (backend + frontend)
2. Check that ports 8000 and 3000 are not blocked
3. Verify Python 3.10+ and Node.js 18+ are installed:
   ```powershell
   python --version
   node --version
   ```

---

**You're all set! Enjoy using STYLO! 🎨👔**
