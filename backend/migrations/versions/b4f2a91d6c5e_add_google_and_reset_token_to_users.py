"""add google_id and reset token fields to users

Revision ID: b4f2a91d6c5e
Revises: 8617ff021a1a
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4f2a91d6c5e'
down_revision: Union[str, Sequence[str], None] = '8617ff021a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token_hash')
    op.drop_column('users', 'google_id')
