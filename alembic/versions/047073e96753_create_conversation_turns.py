"""create_conversation_turns

Revision ID: 047073e96753
Revises: d3a9893495d4
Create Date: 2026-06-09 17:55:45.954680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '047073e96753'
down_revision: Union[str, Sequence[str], None] = 'd3a9893495d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE conversation_turns (
            id UUID PRIMARY KEY,
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            turn_number INTEGER NOT NULL,
            role VARCHAR NOT NULL CHECK (role IN ('user', 'agent')),
            content TEXT NOT NULL,
            intent JSONB,
            tools_called JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        );
        CREATE INDEX idx_conversation_turns_session_id_created_at ON conversation_turns(session_id, created_at DESC);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE conversation_turns;")
