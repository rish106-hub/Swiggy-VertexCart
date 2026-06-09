"""create_order_references

Revision ID: 256c35d2eafe
Revises: 047073e96753
Create Date: 2026-06-09 17:55:46.193936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '256c35d2eafe'
down_revision: Union[str, Sequence[str], None] = '047073e96753'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE order_references (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            vertical VARCHAR NOT NULL CHECK (vertical IN ('food', 'instamart', 'dineout')),
            swiggy_order_id VARCHAR NOT NULL,
            placed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            status VARCHAR DEFAULT 'placed'
        );
        CREATE INDEX idx_order_references_session_id ON order_references(session_id);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE order_references;")
