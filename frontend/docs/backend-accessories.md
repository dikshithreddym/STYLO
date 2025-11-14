# Backend changes to support Accessories

This project now exposes an "accessories" category from the frontend (e.g., sunglasses, rings, belts). If your backend currently rejects it (HTTP 422), update your models and suggestion rules with the steps below.

The examples assume FastAPI + Pydantic + SQLAlchemy. Adapt for your stack as needed.

## 1) Update the category enum/schema

In your Pydantic schema (or type definitions), add `accessories` to the category enum/list.

Example (Pydantic):

```python
# app/schemas.py
from enum import Enum
from pydantic import BaseModel

class Category(str, Enum):
    top = "top"
    bottom = "bottom"
    shoes = "shoes"
    layer = "layer"
    one_piece = "one-piece"  # keep existing naming if used by clients
    accessories = "accessories"

class WardrobeItemCreate(BaseModel):
    type: str
    color: str
    image_url: str | None = None
    category: Category
```

If you validate strings manually, extend your allowed set:

```python
ALLOWED_CATEGORIES = {"top", "bottom", "shoes", "layer", "one-piece", "accessories"}
```

## 2) Update the database model

If you use SQLAlchemy with a DB-level Enum, add the new value. Two common cases:

- SQLite or String column: likely nothing to change at the DB level (just validation). Ensure `String` column accepts the value and update any server-side validators.
- PostgreSQL Enum: you must alter the enum type.

Example SQLAlchemy model (ensure the Python Enum includes `accessories`):

```python
# app/models.py
from sqlalchemy import Column, Integer, String, Enum as SAEnum
from .schemas import Category

class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    color = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    category = Column(SAEnum(Category, name="category"), nullable=False)
```

### Alembic migration (PostgreSQL)

Postgres requires altering the enum type explicitly. Create a migration like:

```python
# alembic revision -m "add accessories category"
from alembic import op

def upgrade():
    op.execute("ALTER TYPE category ADD VALUE IF NOT EXISTS 'accessories';")

def downgrade():
    # Downgrading enums is non-trivial; often left as no-op
    pass
```

Apply the migration:

```bash
alembic upgrade head
```

## 3) Update suggestion rules to use accessories (optional but recommended)

If your suggestions endpoint uses a rules engine, include accessories with simple heuristics:

- Sunny/hot/outdoor: prefer sunglasses, cap.
- Formal/wedding/business: prefer rings, bracelets, watches.
- Cold/windy: prefer scarves, beanies, gloves.
- Belts when bottoms are present and color matches/coordinates.
- Select 0–2 accessories per outfit; adjust score slightly for good complements.

Pseudocode:

```python
def add_accessories(items, context):
    accessories = query_items(category="accessories")
    picks = []

    if context.weather in {"hot", "sunny"}:
        picks += pick(accessories, types=["sunglasses", "cap"], limit=1)

    if context.occasion in {"formal", "wedding", "business"}:
        picks += pick(accessories, types=["ring", "bracelet", "watch"], limit=1)

    if context.weather in {"cold", "windy"}:
        picks += pick(accessories, types=["scarf", "beanie", "gloves"], limit=1)

    if has_bottom(items):
        picks += pick(accessories, types=["belt"], limit=1, color_match=bottom_color(items))

    return items + unique_by_id(picks[:2])
```

## 4) Test

Create an accessory:

```bash
curl -X POST "$API/wardrobe" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "Sunglasses",
    "color": "Black",
    "image_url": null,
    "category": "accessories"
  }'
```

Verify suggestions include accessories where appropriate:

```bash
curl -X POST "$API/suggestions" \
  -H 'Content-Type: application/json' \
  -d '{ "text": "Sunny outdoor brunch, casual" }'
```

---

Once the backend accepts `accessories`, the frontend will add and display them, and the Suggest page will render accessory items alongside other outfit pieces.
