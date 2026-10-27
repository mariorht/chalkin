"""add gym verification

Revision ID: 016_add_gym_verification
Revises: 015_add_competitions
Create Date: 2026-10-27

Adds the verified-gym flag:

- Unverified gyms can be edited by any authenticated user (useful right after
  someone creates one and makes a mistake).
- Verified gyms can only be edited by admins.

Existing gyms are deliberately left unverified, so an admin can review them
before locking them down.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016_add_gym_verification'
down_revision = '015_add_competitions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_gyms_is_verified", ["is_verified"])


def downgrade() -> None:
    with op.batch_alter_table("gyms") as batch_op:
        batch_op.drop_index("ix_gyms_is_verified")
        batch_op.drop_column("verified_at")
        batch_op.drop_column("is_verified")
