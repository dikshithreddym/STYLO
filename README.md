# STYLO - Smart Wardrobe Management System

A modern, production-ready web application for managing your wardrobe with style and intelligence.

## 🎯 Project Overview

STYLO is a full-stack web application that helps users organize and manage their wardrobe digitally. This is **Phase 1** - the core foundation with frontend UI, backend API, and wardrobe management features.

### Phase 1 Features ✅
- ✅ Clean project structure
- ✅ Modern, responsive UI
- ✅ Backend API with FastAPI
- ✅ Frontend with Next.js + TypeScript + Tailwind
- ✅ Wardrobe management (viewing items)
- ✅ API integration
- ✅ Reusable component library

### Not Included in Phase 1 ❌
- ❌ User authentication
- ❌ Sign up / Login
- ❌ User accounts
- ❌ Database integration (using dummy data)

---

## 🏗️ Architecture

```
Stylo_MVP/
├── backend/              # FastAPI Backend
│   ├── app/
│   │   ├── main.py      # FastAPI app & CORS
│   │   ├── models.py    # Database models (future)
│   │   ├── schemas.py   # Pydantic schemas
│   │   └── routers/
│   │       └── wardrobe.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
└── frontend/            # Next.js Frontend
    ├── src/
    │   ├── app/         # Next.js App Router
    │   │   ├── page.tsx           # Landing page
    │   │   ├── dashboard/         # Dashboard
    │   │   └── wardrobe/          # Wardrobe page
    │   ├── components/
    │   │   ├── ui/               # Reusable UI components
    │   │   └── layout/           # Layout components
    │   └── lib/
    │       ├── api.ts           # API wrapper
    │       └── apiClient.ts     # Axios configuration
    ├── package.json
    ├── .env.example
    └── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Backend:** Python 3.10+, pip
- **Frontend:** Node.js 18+, npm

### 1️⃣ Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be running at: **http://localhost:8000**
- API Docs: http://localhost:8000/docs

### 2️⃣ Frontend Setup

```bash
# Navigate to frontend (in a new terminal)
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local

# Run the development server
npm run dev
```

Frontend will be running at: **http://localhost:3000**

---

## 📡 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok"}
```

### Wardrobe
```
GET /wardrobe
Response: [
  {
    "id": 1,
    "type": "T-Shirt",
    "color": "Navy Blue",
    "image_url": "https://..."
  },
  ...
]
```

```
GET /wardrobe/{item_id}
Response: {
  "id": 1,
  "type": "T-Shirt",
  "color": "Navy Blue",
  "image_url": "https://..."
}
```

---

## 🎨 Tech Stack

### Backend
- **Framework:** FastAPI
- **Server:** Uvicorn
- **Validation:** Pydantic
- **CORS:** FastAPI CORS Middleware

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Images:** Next.js Image Optimization

---

## 📂 Key Files

### Backend
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/routers/wardrobe.py` - Wardrobe API endpoints
- `backend/app/schemas.py` - Request/Response schemas

### Frontend
- `frontend/src/app/page.tsx` - Landing page
- `frontend/src/app/dashboard/page.tsx` - Dashboard
- `frontend/src/app/wardrobe/page.tsx` - Wardrobe page (API integration)
- `frontend/src/lib/api.ts` - API client wrapper
- `frontend/src/components/ui/` - Reusable components

---

## 🧪 Testing the Integration

1. Start the backend server (port 8000)
2. Start the frontend dev server (port 3000)
3. Navigate to http://localhost:3000
4. Click "View Wardrobe" to see items fetched from the API

---

## 🔧 Configuration

### Backend Environment Variables
```bash
# backend/.env
APP_NAME=STYLO API
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

### Frontend Environment Variables
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 📝 Development Notes

### Current State (Phase 1)
- All data is currently **dummy data** stored in memory
- No database connection
- No authentication required
- CORS configured for localhost development
- 10 sample wardrobe items with Unsplash images

### Planned for Future Phases
- User authentication & authorization
- Database integration (PostgreSQL/MongoDB)
- User-specific wardrobes
- Add/Edit/Delete wardrobe items
- Outfit creation & styling recommendations
- Image upload functionality
- Analytics & insights

---

## 🎯 Next Steps

To continue development:

1. **Add Database:** Integrate PostgreSQL/MongoDB
2. **Authentication:** Implement JWT-based auth
3. **CRUD Operations:** Add create/update/delete for wardrobe items
4. **File Upload:** Add image upload functionality
5. **Outfit Builder:** Create outfit combination feature
6. **Analytics:** Track wardrobe usage patterns

---

## 📄 License

This project is for educational/demonstration purposes.

---

## 🙋‍♂️ Support

For issues or questions:
1. Check the README files in `backend/` and `frontend/` directories
2. Review the API documentation at http://localhost:8000/docs
3. Ensure both servers are running on the correct ports

---

**Built with ❤️ for stylish wardrobe management**
