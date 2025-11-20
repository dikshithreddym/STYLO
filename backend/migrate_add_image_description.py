"""
Idempotent migration: ensure wardrobe_items.image_description exists.
Works on SQLite and Postgres using SQLAlchemy Inspector.
"""
from sqlalchemy import inspect, text
from app.database import engine, Base
from app.database import WardrobeItem  # noqa: F401 - ensure model is registered


def migrate() -> None:
    """Ensure image_description column exists, creating table if needed."""
    # Ensure tables exist (no-op if already created)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        insp = inspect(conn)
        # Create table if missing
        if not insp.has_table("wardrobe_items"):
            Base.metadata.create_all(bind=engine)

        cols = [c["name"] for c in insp.get_columns("wardrobe_items")]
        if "image_description" not in cols:
            conn.execute(text("ALTER TABLE wardrobe_items ADD COLUMN image_description TEXT"))
            print("✅ Added image_description column to wardrobe_items")
        else:
            print("ℹ️  image_description column already present; no changes needed")


if __name__ == "__main__":
    migrate()
