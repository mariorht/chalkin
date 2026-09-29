"""add competitions (league events)

Revision ID: 015_add_competitions
Revises: 014_add_exercise_grip
Create Date: 2026-09-29

Adds league events (e.g. the Boulder Up Superliga):

- ``competitions``: event tied to a gym, with a date range and status.
- ``competition_points``: points per grade for the event.
- ``ascents.competition_id``: tags an ascent as a league block.

Weeks are derived from the calendar, so there is no week table.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_add_competitions'
down_revision = '014_add_exercise_grip'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("gym_id", sa.Integer(), sa.ForeignKey("gyms.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("week_offsets", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "ACTIVE", "FINISHED", name="competitionstatus"),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_competitions_gym_id", "competitions", ["gym_id"])

    op.create_table(
        "competition_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grade_id",
            sa.Integer(),
            sa.ForeignKey("grades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "competition_id", "grade_id", name="unique_competition_grade_points"
        ),
    )
    op.create_index(
        "ix_competition_points_competition_id", "competition_points", ["competition_id"]
    )
    op.create_index(
        "ix_competition_points_grade_id", "competition_points", ["grade_id"]
    )

    with op.batch_alter_table("ascents") as batch_op:
        batch_op.add_column(sa.Column("competition_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_ascents_competition_id", ["competition_id"])


def downgrade() -> None:
    with op.batch_alter_table("ascents") as batch_op:
        batch_op.drop_index("ix_ascents_competition_id")
        batch_op.drop_column("competition_id")

    op.drop_index(
        "ix_competition_points_grade_id", table_name="competition_points"
    )
    op.drop_index(
        "ix_competition_points_competition_id", table_name="competition_points"
    )
    op.drop_table("competition_points")

    op.drop_index("ix_competitions_gym_id", table_name="competitions")
    op.drop_table("competitions")
