"""hash existing invitation tokens

Revision ID: 011_hash_invitation_tokens
Revises: 010_add_admin_and_password_resets
Create Date: 2026-09-21
"""

import hashlib

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_hash_invitation_tokens'
down_revision = '010_add_admin_and_password_resets'
branch_labels = None
depends_on = None


def _is_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def upgrade() -> None:
    """Replace plaintext invitation tokens with their SHA-256 hash."""
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, token FROM invitations")).fetchall()
    for row in rows:
        if _is_sha256_hex(row.token):
            continue
        digest = hashlib.sha256(row.token.encode("utf-8")).hexdigest()
        conn.execute(
            sa.text("UPDATE invitations SET token = :token WHERE id = :id"),
            {"token": digest, "id": row.id},
        )


def downgrade() -> None:
    # One-way: plaintext tokens cannot be recovered from their hash.
    pass
