"""
Migration script to add is_pinned column to saved_outfits table.
Run this script once to update the database schema.

Usage:
    cd backend
    python -m Verification\ or\ TestFiles.migrate_add_is_pinned
    
Or from project root:
    python backend/Verification\ or\ TestFiles/migrate_add_is_pinned.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Add is_pinned column to saved_outfits table"""
    
    with engine.begin() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'saved_outfits' AND column_name = 'is_pinned'
        """))
        
        if result.fetchone():
            print("✓ Column 'is_pinned' already exists in saved_outfits table")
            return
        
        # Add the column
        print("Adding 'is_pinned' column to saved_outfits table...")
        conn.execute(text("""
            ALTER TABLE saved_outfits 
            ADD COLUMN is_pinned INTEGER DEFAULT 0 NOT NULL
        """))
        print("✓ Successfully added 'is_pinned' column to saved_outfits table")

if __name__ == "__main__":
    migrate()
