"""create_sessions

Revision ID: d3a9893495d4
Revises: 
Create Date: 2026-06-09 17:55:34.209540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3a9893495d4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE sessions (
            id UUID PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            swiggy_access_token TEXT,
            token_expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            last_active_at TIMESTAMP WITH TIME ZONE
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE sessions;")
