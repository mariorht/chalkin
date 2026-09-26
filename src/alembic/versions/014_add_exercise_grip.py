"""add grip to session_exercises

Revision ID: 014_add_exercise_grip
Revises: 013_add_sense_reps
Create Date: 2026-09-26

Adds ``grip`` to session_exercises, so block/edge lifts can record how the
implement was held (open hand, half crimp, full crimp, pinch, mono...).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014_add_exercise_grip'
down_revision = '013_add_sense_reps'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("session_exercises") as batch_op:
        batch_op.add_column(sa.Column("grip", sa.String(length=30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("session_exercises") as batch_op:
        batch_op.drop_column("grip")
