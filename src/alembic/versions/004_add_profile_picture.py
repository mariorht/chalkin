"""Add profile_picture to users

Revision ID: 004_add_profile_picture
Revises: 003_add_session_title
Create Date: 2025-12-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_profile_picture'
down_revision = '003_add_session_title'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('profile_picture', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('users', 'profile_picture')
