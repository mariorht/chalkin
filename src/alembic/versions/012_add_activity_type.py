"""add activity_type and make gym_id nullable

Revision ID: 012_add_activity_type
Revises: 011_hash_invitation_tokens
Create Date: 2026-09-26

Introduces ``sessions.activity_type`` (gym | home) and makes ``sessions.gym_id``
nullable so users can log training activities not tied to a gym. Existing rows
are backfilled as ``GYM``.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012_add_activity_type'
down_revision = '011_hash_invitation_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "activity_type",
                sa.Enum("GYM", "HOME", name="activitytype"),
                nullable=False,
                server_default="GYM",
            )
        )
        batch_op.alter_column(
            "gym_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    # NOTE: this fails if there are home sessions (gym_id IS NULL). Remove them
    # first if you really need to roll back.
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("activity_type")
        batch_op.alter_column(
            "gym_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
