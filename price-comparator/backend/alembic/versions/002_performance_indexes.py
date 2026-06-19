"""Performance indexes and pg_trgm for fast product search

Revision ID: 002
Revises: 001
Create Date: 2026-06-18
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # GIN trigram index — makes ILIKE '%term%' queries ~100x faster
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_products_name_trgm "
        "ON market_products USING gin (name gin_trgm_ops)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_products_available_price "
        "ON market_products (is_available, price) WHERE is_available = true"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_products_market_available "
        "ON market_products (market_id, is_available)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_market_products_last_updated "
        "ON market_products (last_updated DESC)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_price_history_checked_at "
        "ON price_history (market_product_id, checked_at DESC)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_search_history_created_at "
        "ON search_history (created_at DESC)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scraping_jobs_status "
        "ON scraping_jobs (status, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scraping_jobs_status")
    op.execute("DROP INDEX IF EXISTS ix_search_history_created_at")
    op.execute("DROP INDEX IF EXISTS ix_price_history_checked_at")
    op.execute("DROP INDEX IF EXISTS ix_market_products_last_updated")
    op.execute("DROP INDEX IF EXISTS ix_market_products_market_available")
    op.execute("DROP INDEX IF EXISTS ix_market_products_available_price")
    op.execute("DROP INDEX IF EXISTS ix_market_products_name_trgm")
