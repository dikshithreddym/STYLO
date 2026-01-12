"""
Migration script to convert embedding column from JSON to ARRAY(FLOAT) type.
This provides better performance for vector operations in PostgreSQL.

Run this once to migrate existing databases:
    python migrate_embedding_to_array.py

Or from project root:
    python "Verification or TestFiles/migrate_embedding_to_array.py"
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine


def migrate_embedding_column():
    """Migrate embedding column from JSON to ARRAY(FLOAT) type"""
    with engine.connect() as connection:
        try:
            # Check database dialect
            dialect = engine.dialect.name
            print(f"Database dialect: {dialect}")
            
            if dialect != 'postgresql':
                print(f"Note: {dialect} does not support native ARRAY types.")
                print("The VectorType in the model will use JSON as fallback.")
                print("No migration needed for non-PostgreSQL databases.")
                return
            
            # Check if column exists and its current type
            result = connection.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'wardrobe_items' AND column_name = 'embedding'
            """))
            row = result.fetchone()
            
            if not row:
                # Column doesn't exist - create it with correct type
                print("Embedding column doesn't exist. Creating with FLOAT[] type...")
                connection.execute(text("""
                    ALTER TABLE wardrobe_items
                    ADD COLUMN embedding FLOAT[]
                """))
                connection.commit()
                print("SUCCESS: Created embedding column with FLOAT[] type")
                return
            
            current_type = row[0].lower()
            print(f"Current embedding column type: {current_type}")
            
            if current_type in ('double precision[]', 'real[]', 'float[]', 'array'):
                print("SUCCESS: Embedding column already uses array type. No migration needed.")
                return
            
            if current_type in ('json', 'jsonb'):
                print("Migrating from JSON to FLOAT[] type...")
                
                # Step 1: Create temporary column with correct type
                print("  Step 1: Creating temporary column...")
                connection.execute(text("""
                    ALTER TABLE wardrobe_items
                    ADD COLUMN embedding_new FLOAT[]
                """))
                connection.commit()
                
                # Step 2: Convert and copy data
                print("  Step 2: Converting JSON data to array format...")
                # PostgreSQL can convert JSON array to native array
                connection.execute(text("""
                    UPDATE wardrobe_items 
                    SET embedding_new = (
                        SELECT ARRAY(
                            SELECT CAST(value AS FLOAT)
                            FROM json_array_elements_text(embedding::json)
                        )
                    )
                    WHERE embedding IS NOT NULL
                """))
                connection.commit()
                
                # Step 3: Drop old column
                print("  Step 3: Dropping old JSON column...")
                connection.execute(text("""
                    ALTER TABLE wardrobe_items
                    DROP COLUMN embedding
                """))
                connection.commit()
                
                # Step 4: Rename new column
                print("  Step 4: Renaming new column...")
                connection.execute(text("""
                    ALTER TABLE wardrobe_items
                    RENAME COLUMN embedding_new TO embedding
                """))
                connection.commit()
                
                print("SUCCESS: Migrated embedding column from JSON to FLOAT[] type")
                
            else:
                print(f"WARNING: Unknown column type '{current_type}'. Manual migration may be required.")
                
        except Exception as e:
            print(f"ERROR: Migration failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Embedding Column Migration: JSON -> FLOAT[]")
    print("=" * 60)
    print()
    migrate_embedding_column()
    print()
    print("Migration complete!")
