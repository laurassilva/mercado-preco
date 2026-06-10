"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "markets",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("integration_type", sa.String(50), server_default="scraping", nullable=False),
        sa.Column("scraper_class", sa.String(255), server_default="mock"),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "product_groups",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("brand", sa.String(255)),
        sa.Column("quantity", sa.String(100)),
        sa.Column("unit", sa.String(50)),
        sa.Column("category", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "market_products",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("market_id", UUID(as_uuid=True), sa.ForeignKey("markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_group_id", UUID(as_uuid=True), sa.ForeignKey("product_groups.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("brand", sa.String(255)),
        sa.Column("quantity", sa.String(100)),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("image_url", sa.String(1000)),
        sa.Column("product_url", sa.String(1000)),
        sa.Column("is_available", sa.Boolean, server_default="true"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_market_products_market_id", "market_products", ["market_id"])
    op.create_index("ix_market_products_group_id", "market_products", ["product_group_id"])

    op.create_table(
        "price_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("market_product_id", UUID(as_uuid=True), sa.ForeignKey("market_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_price_history_product_id", "price_history", ["market_product_id"])

    op.create_table(
        "search_history",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("results_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"])

    op.create_table(
        "scraping_jobs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("market_id", UUID(as_uuid=True), sa.ForeignKey("markets.id", ondelete="SET NULL")),
        sa.Column("query", sa.String(500)),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("results_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("scraping_jobs")
    op.drop_table("search_history")
    op.drop_table("price_history")
    op.drop_table("market_products")
    op.drop_table("product_groups")
    op.drop_table("markets")
    op.drop_table("users")
