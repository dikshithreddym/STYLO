# STYLO Backend API

FastAPI backend for the STYLO wardrobe management application.

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows:
  ```bash
  .\venv\Scripts\activate
  ```
- macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create a `.env` file (optional):
```bash
cp .env.example .env
```

## Running the Application

Start the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs (Swagger): http://localhost:8000/docs
- Alternative API docs (ReDoc): http://localhost:8000/redoc

## API Endpoints

### Health Check
- `GET /health` - Returns API health status

### Wardrobe
- `GET /wardrobe` - Get all wardrobe items
- `GET /wardrobe/{item_id}` - Get specific wardrobe item

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application & CORS setup
│   ├── models.py         # Database models (future)
│   ├── schemas.py        # Pydantic schemas
│   └── routers/
│       ├── __init__.py
│       └── wardrobe.py   # Wardrobe endpoints
├── requirements.txt
├── .env.example
└── README.md
```

## Development Notes

- Currently using dummy in-memory data
- No database integration yet
- No authentication implemented yet
- CORS configured for http://localhost:3000 (frontend)
