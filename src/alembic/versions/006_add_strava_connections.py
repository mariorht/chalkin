"""add strava connections table

Revision ID: 006_add_strava_connections
Revises: 005_add_push_subscriptions
Create Date: 2025-12-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_strava_connections'
down_revision = '005_add_push_subscriptions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strava_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('athlete_id', sa.BigInteger(), nullable=False),
        sa.Column('access_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.BigInteger(), nullable=False),
        sa.Column('scope', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_strava_connections_id'), 'strava_connections', ['id'], unique=False)
    op.create_index(op.f('ix_strava_connections_athlete_id'), 'strava_connections', ['athlete_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_strava_connections_athlete_id'), table_name='strava_connections')
    op.drop_index(op.f('ix_strava_connections_id'), table_name='strava_connections')
    op.drop_table('strava_connections')
