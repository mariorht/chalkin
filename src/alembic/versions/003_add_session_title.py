"""Add title and subtitle to sessions

Revision ID: 003_add_session_title
Revises: 002_add_friendships
Create Date: 2025-12-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_session_title'
down_revision = '002_add_friendships'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sessions', sa.Column('title', sa.String(100), nullable=True))
    op.add_column('sessions', sa.Column('subtitle', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('sessions', 'subtitle')
    op.drop_column('sessions', 'title')
