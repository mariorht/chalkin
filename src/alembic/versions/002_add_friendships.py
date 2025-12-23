"""add friendships table

Revision ID: 002_add_friendships
Revises: 001_initial
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_friendships'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'friendships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('friend_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['friend_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'friend_id', name='uix_friendship')
    )
    op.create_index(op.f('ix_friendships_user_id'), 'friendships', ['user_id'], unique=False)
    op.create_index(op.f('ix_friendships_friend_id'), 'friendships', ['friend_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_friendships_friend_id'), table_name='friendships')
    op.drop_index(op.f('ix_friendships_user_id'), table_name='friendships')
    op.drop_table('friendships')
