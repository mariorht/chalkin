"""add invitations table

Revision ID: 008_add_invitations
Revises: 007_add_strava_to_sessions
Create Date: 2025-12-31
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_add_invitations'
down_revision = '007_add_strava_to_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('used_by_user_id', sa.Integer(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['used_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invitations_id'), 'invitations', ['id'], unique=False)
    op.create_index(op.f('ix_invitations_token'), 'invitations', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_invitations_token'), table_name='invitations')
    op.drop_index(op.f('ix_invitations_id'), table_name='invitations')
    op.drop_table('invitations')
