"""rag project isolation schema fixes

Revision ID: 4b1d1134b860
Revises: b4f2a91d6c5e
Create Date: 2026-08-24 09:34:18.122200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '4b1d1134b860'
down_revision: Union[str, Sequence[str], None] = 'b4f2a91d6c5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("rag_chunks_paper_id_fkey", "rag_chunks", type_="foreignkey")
    op.create_foreign_key(
        "rag_chunks_paper_id_fkey", "rag_chunks", "rag_papers",
        ["paper_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_rag_papers_project_id", "rag_papers", ["project_id"])
    op.create_index("ix_rag_chunks_paper_id", "rag_chunks", ["paper_id"])
    op.drop_column("rag_chunks", "embedding")
    op.add_column(
        "rag_chunks",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rag_chunks", "embedding")
    op.add_column(
        "rag_chunks",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=False),
    )
    op.drop_index("ix_rag_chunks_paper_id", table_name="rag_chunks")
    op.drop_index("ix_rag_papers_project_id", table_name="rag_papers")
    op.drop_constraint("rag_chunks_paper_id_fkey", "rag_chunks", type_="foreignkey")
    op.create_foreign_key(
        "rag_chunks_paper_id_fkey", "rag_chunks", "rag_papers",
        ["paper_id"], ["id"],
    )
