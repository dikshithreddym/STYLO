# Embedding Column Migration Guide

This guide explains how to add the `embedding` column to your database for the embedding persistence feature.

## Prerequisites

1. Make sure you have Python dependencies installed:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Ensure your `DATABASE_URL` environment variable is set (or it will use the default)

## Running the Migration

### Option 1: Run from backend directory (Recommended)

```bash
cd backend
python migrate_add_embedding_column.py
```

### Option 2: Run from project root

```bash
cd backend
python "Verification or TestFiles/migrate_add_embedding_column.py"
```

### Option 3: Using Python module syntax

```bash
cd backend
python -m "Verification or TestFiles.migrate_add_embedding_column"
```

## Expected Output

**Success (column added):**
```
SUCCESS: Successfully added embedding column to wardrobe_items table
```

**Success (column already exists):**
```
SUCCESS: Embedding column already exists
```

**Error (dependencies not installed):**
```
ERROR: Import error: No module named 'sqlalchemy'
Make sure you:
   1. Are in the 'backend' directory
   2. Have activated your virtual environment
   3. Have installed dependencies: pip install -r requirements.txt
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"

**Solution:** Install dependencies first:
```bash
cd backend
pip install -r requirements.txt
```

If using a virtual environment:
```bash
# Activate virtual environment first
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Then install dependencies
pip install -r requirements.txt
```

### "ERROR: Error adding embedding column"

**Possible causes:**
1. Database connection issue - check `DATABASE_URL` environment variable
2. Insufficient permissions - ensure database user has `ALTER TABLE` permissions
3. Database not accessible - verify network connectivity

### Unicode/Encoding Errors in Windows PowerShell

The migration script now uses ASCII characters to avoid encoding issues. If you still see encoding errors, try running in Command Prompt instead of PowerShell, or set:
```powershell
$env:PYTHONIOENCODING="utf-8"
```

## What This Migration Does

- Adds a `embedding` column (JSON type) to the `wardrobe_items` table
- The column stores pre-computed embedding vectors as JSON arrays
- This enables faster suggestion queries by avoiding redundant embedding computations
- The migration is **idempotent** - safe to run multiple times

## After Migration

Once the migration completes:
1. Existing items will have `NULL` embeddings (computed on-demand when needed)
2. New items will automatically queue embedding computation in the background
3. You can batch-refresh embeddings using: `POST /wardrobe/refresh-embeddings`

## Verification

To verify the column was added, you can check your database:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'wardrobe_items' AND column_name = 'embedding';
```

Or use the admin endpoint to refresh embeddings for existing items:
```bash
curl -X POST http://localhost:8000/wardrobe/refresh-embeddings
```

