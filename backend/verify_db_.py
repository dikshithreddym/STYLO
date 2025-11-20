from app.database import SessionLocal

db = SessionLocal()
try:
    db.execute("SELECT 1")
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
finally:
    db.close()