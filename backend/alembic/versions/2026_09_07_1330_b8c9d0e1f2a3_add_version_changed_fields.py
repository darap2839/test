"""add changed fields to document versions

Revision ID: 2026_09_07_1330_b8c9d0e1f2a3
Revises: 2026_09_07_1200_a7b8c9d0e1f2
Create Date: 2026-09-07 13:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2026_09_07_1330_b8c9d0e1f2a3"
down_revision: Union[str, None] = "2026_09_07_1200_a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column(
            "changed_fields",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "changed_fields")
