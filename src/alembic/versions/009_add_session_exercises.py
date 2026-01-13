"""add session exercises table

Revision ID: 009_add_session_exercises
Revises: 008_add_invitations
Create Date: 2026-01-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_add_session_exercises'
down_revision = '008_add_invitations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'session_exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('exercise_type', sa.String(length=50), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.String(length=50), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_exercises_id'), 'session_exercises', ['id'], unique=False)
    op.create_index(op.f('ix_session_exercises_session_id'), 'session_exercises', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_session_exercises_session_id'), table_name='session_exercises')
    op.drop_index(op.f('ix_session_exercises_id'), table_name='session_exercises')
    op.drop_table('session_exercises')
