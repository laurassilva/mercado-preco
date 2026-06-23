"""Add categories, price_alerts, and category column to market_products

Revision ID: 004
Revises: 003
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Categories table
    op.create_table(
        "categories",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("keywords", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Category column on market_products
    op.add_column("market_products", sa.Column("category", sa.String(100), nullable=True))
    op.create_index("ix_market_products_category", "market_products", ["category"], postgresql_where=sa.text("category IS NOT NULL"))

    # Price alerts table
    op.create_table(
        "price_alerts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("market_product_id", UUID(as_uuid=True), sa.ForeignKey("market_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("market_id", UUID(as_uuid=True), sa.ForeignKey("markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("old_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_diff", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_diff_pct", sa.Numeric(8, 2), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_price_alerts_detected_at", "price_alerts", [sa.text("detected_at DESC")])
    op.create_index("ix_price_alerts_market_id", "price_alerts", ["market_id"])
    op.create_index("ix_price_alerts_type", "price_alerts", ["alert_type", sa.text("detected_at DESC")])
    op.create_index("ix_price_alerts_category", "price_alerts", ["category"], postgresql_where=sa.text("category IS NOT NULL"))


def downgrade() -> None:
    op.drop_table("price_alerts")
    op.drop_index("ix_market_products_category", table_name="market_products")
    op.drop_column("market_products", "category")
    op.drop_table("categories")
