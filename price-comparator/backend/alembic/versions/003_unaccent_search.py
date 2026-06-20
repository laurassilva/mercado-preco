"""Add unaccent extension for accent-insensitive product search

Revision ID: 003
Revises: 002
Create Date: 2026-06-20
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    op.execute("""
        CREATE OR REPLACE FUNCTION f_unaccent(text)
        RETURNS text AS $$
            SELECT public.unaccent('public.unaccent', $1)
        $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_products_name_unaccent_trgm "
        "ON market_products USING gin (f_unaccent(name) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_market_products_name_unaccent_trgm")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
