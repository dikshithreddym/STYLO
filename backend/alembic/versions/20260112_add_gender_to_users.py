"""add gender column to users

Revision ID: add_gender_to_users_20260112
Revises: 
Create Date: 2026-01-12 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_gender_to_users_20260112'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('gender', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'gender')
