"""add pdf_hash to frameworks

Revision ID: c3f1a7d2e9b4
Revises: 4b1d1134b860
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3f1a7d2e9b4'
down_revision: Union[str, Sequence[str], None] = '4b1d1134b860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('frameworks', sa.Column('pdf_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_frameworks_pdf_hash', 'frameworks', ['pdf_hash'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_frameworks_pdf_hash', table_name='frameworks')
    op.drop_column('frameworks', 'pdf_hash')
