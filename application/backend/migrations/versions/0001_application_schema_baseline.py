"""Establish migration history without inventing product tables.

Revision ID: 0001_application_schema_baseline
Revises:
Create Date: 2026-11-02
"""

from collections.abc import Sequence

revision: str = "0001_application_schema_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
