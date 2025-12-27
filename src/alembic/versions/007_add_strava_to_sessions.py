"""add strava activity id to sessions

Revision ID: 007_add_strava_to_sessions
Revises: 006_add_strava_connections
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_strava_to_sessions'
down_revision = '006_add_strava_connections'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('strava_activity_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'strava_activity_id')
