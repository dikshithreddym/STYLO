"""
Migration script to add performance indexes to wardrobe_items table.
Run this to optimize query performance for common access patterns.

Usage:
    cd backend
    python migrate_add_indexes.py
"""
import os
import sys

try:
    from sqlalchemy import text, inspect
    from app.database import engine, SessionLocal
except ImportError as e:
    print(f"ERROR: Import error: {e}")
    print("\nMake sure you:")
    print("   1. Are in the 'backend' directory")
    print("   2. Have activated your virtual environment")
    print("   3. Have installed dependencies: pip install -r requirements.txt")
    print(f"\n   Current working directory: {os.getcwd()}")
    sys.exit(1)

def get_existing_indexes(conn, table_name: str) -> set:
    """Get set of existing index names for a table"""
    insp = inspect(conn)
    indexes = insp.get_indexes(table_name)
    return {idx['name'] for idx in indexes}

def migrate():
    """Add performance indexes to wardrobe_items table"""
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            insp = inspect(conn)
            existing_indexes = get_existing_indexes(conn, "wardrobe_items")
            
            indexes_to_create = []
            
            # Composite index for category + embedding (common query: items with embeddings by category)
            if "ix_wardrobe_items_category_embedding" not in existing_indexes:
                indexes_to_create.append({
                    "name": "ix_wardrobe_items_category_embedding",
                    "sql": """
                        CREATE INDEX ix_wardrobe_items_category_embedding 
                        ON wardrobe_items(category) 
                        WHERE embedding IS NOT NULL
                    """,
                    "description": "Partial index for category queries on items with embeddings"
                })
            
            # Composite index for type + color (common filter combination)
            if "ix_wardrobe_items_type_color" not in existing_indexes:
                indexes_to_create.append({
                    "name": "ix_wardrobe_items_type_color",
                    "sql": """
                        CREATE INDEX ix_wardrobe_items_type_color 
                        ON wardrobe_items(type, color)
                    """,
                    "description": "Composite index for type and color filtering"
                })
            
            # Index for items without embeddings (for batch refresh queries)
            if "ix_wardrobe_items_embedding_null" not in existing_indexes:
                indexes_to_create.append({
                    "name": "ix_wardrobe_items_embedding_null",
                    "sql": """
                        CREATE INDEX ix_wardrobe_items_embedding_null 
                        ON wardrobe_items(id) 
                        WHERE embedding IS NULL
                    """,
                    "description": "Partial index for finding items without embeddings"
                })
            
            # Composite index for category + type (common filter)
            if "ix_wardrobe_items_category_type" not in existing_indexes:
                indexes_to_create.append({
                    "name": "ix_wardrobe_items_category_type",
                    "sql": """
                        CREATE INDEX ix_wardrobe_items_category_type 
                        ON wardrobe_items(category, type)
                    """,
                    "description": "Composite index for category and type filtering"
                })
            
            if not indexes_to_create:
                print("SUCCESS: All performance indexes already exist")
                return
            
            # Create indexes
            created = 0
            for idx_info in indexes_to_create:
                try:
                    db.execute(text(idx_info["sql"]))
                    db.commit()
                    print(f"SUCCESS: Created index '{idx_info['name']}' - {idx_info['description']}")
                    created += 1
                except Exception as e:
                    db.rollback()
                    print(f"WARNING: Failed to create index '{idx_info['name']}': {e}")
            
            if created > 0:
                print(f"\nSUCCESS: Created {created} performance index(es)")
            
    except Exception as e:
        db.rollback()
        print(f"ERROR: Error adding indexes: {e}")
        print(f"\nTroubleshooting:")
        print("   - Make sure DATABASE_URL is set correctly")
        print("   - Check that the database is accessible")
        print("   - Verify you have CREATE INDEX permissions")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

