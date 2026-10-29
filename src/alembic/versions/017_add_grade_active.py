"""add is_active to grades

Revision ID: 017_add_grade_active
Revises: 016_add_gym_verification
Create Date: 2026-10-29

Grades that already have ascents cannot be deleted without destroying the
history that references them. Instead they are archived: hidden from the
picker for new ascents, but kept so old sessions still show their colour and
label. Existing grades stay active.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017_add_grade_active'
down_revision = '016_add_gym_verification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("grades") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.create_index("ix_grades_is_active", ["is_active"])


def downgrade() -> None:
    with op.batch_alter_table("grades") as batch_op:
        batch_op.drop_index("ix_grades_is_active")
        batch_op.drop_column("is_active")
