"""Add failed state to enum type

Revision ID: 1099b8b292cc
Revises: baf15e3018b0
Create Date: 2026-07-05 19:23:32.571072

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1099b8b292cc'
down_revision: Union[str, Sequence[str], None] = 'baf15e3018b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE ingestion_batch_status ADD VALUE IF NOT EXISTS 'failed'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enum types; removing 'failed' requires
    # recreating the type, so this migration is not reversible.
    pass
