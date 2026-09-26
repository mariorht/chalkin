"""add sense_reps and fingerboard context to session_exercises

Revision ID: 013_add_sense_reps
Revises: 012_add_activity_type
Create Date: 2026-09-26

Stores force reps measured with Chalkin Sense, attached to a SessionExercise,
plus fingerboard context fields (protocol, edge depth, hand, weights).

No raw curves are stored for training reps; ``sense_reps.curve`` is reserved
and left NULL for now.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013_add_sense_reps'
down_revision = '012_add_activity_type'
branch_labels = None
depends_on = None

_EXERCISE_CONTEXT_COLUMNS = (
    sa.Column("protocol", sa.String(length=50), nullable=True),
    sa.Column("edge_depth_mm", sa.Integer(), nullable=True),
    sa.Column("hand", sa.String(length=10), nullable=True),
    sa.Column("added_weight_kg", sa.Float(), nullable=True),
    sa.Column("body_weight_kg", sa.Float(), nullable=True),
)


def upgrade() -> None:
    op.create_table(
        "sense_reps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "exercise_id",
            sa.Integer(),
            sa.ForeignKey("session_exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("set_index", sa.Integer(), nullable=True),
        sa.Column("rep_index", sa.Integer(), nullable=True),
        sa.Column("peak_force_kg", sa.Float(), nullable=True),
        sa.Column("mean_force_kg", sa.Float(), nullable=True),
        sa.Column("rfd_kg_s", sa.Float(), nullable=True),
        sa.Column("tut_s", sa.Float(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("calibration_zero", sa.Float(), nullable=True),
        sa.Column("calibration_scale", sa.Float(), nullable=True),
        sa.Column("curve", sa.Text(), nullable=True),
        sa.Column("measured_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_sense_reps_exercise_id", "sense_reps", ["exercise_id"])
    op.create_index("ix_sense_reps_session_id", "sense_reps", ["session_id"])

    with op.batch_alter_table("session_exercises") as batch_op:
        for column in _EXERCISE_CONTEXT_COLUMNS:
            batch_op.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("session_exercises") as batch_op:
        for column in _EXERCISE_CONTEXT_COLUMNS:
            batch_op.drop_column(column.name)

    op.drop_index("ix_sense_reps_session_id", table_name="sense_reps")
    op.drop_index("ix_sense_reps_exercise_id", table_name="sense_reps")
    op.drop_table("sense_reps")
