"""Master Product Catalog (GTIN) — evolve product_groups into master_products

Revision ID: 006
Revises: 005
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Evolve product_groups -> master_products (metadata-only rename, no data loss) ──
    op.rename_table("product_groups", "master_products")

    op.add_column("master_products", sa.Column("gtin", sa.String(14), nullable=True))
    op.add_column("master_products", sa.Column("manufacturer", sa.String(255), nullable=True))
    op.add_column("master_products", sa.Column("subcategory", sa.String(255), nullable=True))
    op.add_column("master_products", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("master_products", sa.Column("volume_base", sa.Numeric(12, 3), nullable=True))
    op.add_column("master_products", sa.Column("volume_base_unit", sa.String(5), nullable=True))
    op.add_column("master_products", sa.Column("image_url", sa.String(1000), nullable=True))
    op.add_column("master_products", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("master_products", sa.Column("gtin_source", sa.String(20), nullable=True))
    op.add_column("master_products", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))

    op.execute("ALTER INDEX IF EXISTS product_groups_pkey RENAME TO master_products_pkey")

    op.execute(
        "CREATE UNIQUE INDEX ix_master_products_gtin ON master_products (gtin) WHERE gtin IS NOT NULL"
    )
    op.execute("CREATE INDEX ix_master_products_category ON master_products (category)")
    op.execute("CREATE INDEX ix_master_products_brand ON master_products (brand)")
    op.execute(
        "CREATE INDEX ix_master_products_name_trgm ON master_products USING gin (f_unaccent(canonical_name) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_master_products_brand_trgm ON master_products USING gin (f_unaccent(brand) gin_trgm_ops)"
    )

    # ── 2. market_products: rename FK, add GTIN + matching metadata ──
    op.alter_column("market_products", "product_group_id", new_column_name="master_product_id")
    op.execute("ALTER INDEX IF EXISTS ix_market_products_group_id RENAME TO ix_market_products_master_product_id")

    op.add_column("market_products", sa.Column("gtin", sa.String(14), nullable=True))
    op.add_column("market_products", sa.Column("match_status", sa.String(20), server_default="unmatched", nullable=False))
    op.add_column("market_products", sa.Column("match_confidence", sa.Numeric(5, 2), nullable=True))
    op.add_column("market_products", sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("market_products", sa.Column("original_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("market_products", sa.Column("is_promotion", sa.Boolean(), server_default="false", nullable=False))

    op.execute("CREATE INDEX ix_market_products_gtin ON market_products (gtin)")
    op.execute(
        "CREATE INDEX ix_market_products_pending_review ON market_products (match_status) WHERE match_status = 'pending_review'"
    )

    # Backfill: products already linked under the old fuzzy grouping become "matched_legacy"
    # (kept linked, but flagged so they can be re-validated once the GTIN catalog is imported)
    op.execute(
        "UPDATE market_products SET match_status = 'matched_legacy', matched_at = created_at "
        "WHERE master_product_id IS NOT NULL"
    )

    # ── 3. Manual review queue ──
    op.create_table(
        "product_match_reviews",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("market_product_id", UUID(as_uuid=True), sa.ForeignKey("market_products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_master_product_id", UUID(as_uuid=True), sa.ForeignKey("master_products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("suggested_gtin", sa.String(14), nullable=True),
        sa.Column("similarity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("match_reasons", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_master_product_id", UUID(as_uuid=True), sa.ForeignKey("master_products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_product_match_reviews_market_product", "product_match_reviews", ["market_product_id"])
    op.execute(
        "CREATE INDEX ix_product_match_reviews_status ON product_match_reviews (status, created_at DESC)"
    )

    # ── 4. GTIN spreadsheet import audit log ──
    op.create_table(
        "master_product_import_batches",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inserted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("errors", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_master_product_import_batches_created ON master_product_import_batches (created_at DESC)"
    )


def downgrade() -> None:
    op.drop_table("master_product_import_batches")
    op.drop_index("ix_product_match_reviews_market_product", table_name="product_match_reviews")
    op.execute("DROP INDEX IF EXISTS ix_product_match_reviews_status")
    op.drop_table("product_match_reviews")

    op.execute("DROP INDEX IF EXISTS ix_market_products_pending_review")
    op.execute("DROP INDEX IF EXISTS ix_market_products_gtin")
    for col in ("is_promotion", "original_price", "matched_at", "match_confidence", "match_status", "gtin"):
        op.drop_column("market_products", col)

    op.execute("ALTER INDEX IF EXISTS ix_market_products_master_product_id RENAME TO ix_market_products_group_id")
    op.alter_column("market_products", "master_product_id", new_column_name="product_group_id")

    op.execute("DROP INDEX IF EXISTS ix_master_products_brand_trgm")
    op.execute("DROP INDEX IF EXISTS ix_master_products_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_master_products_brand")
    op.execute("DROP INDEX IF EXISTS ix_master_products_category")
    op.execute("DROP INDEX IF EXISTS ix_master_products_gtin")

    for col in ("updated_at", "gtin_source", "is_active", "image_url", "volume_base_unit",
                "volume_base", "description", "subcategory", "manufacturer", "gtin"):
        op.drop_column("master_products", col)

    op.execute("ALTER INDEX IF EXISTS master_products_pkey RENAME TO product_groups_pkey")
    op.rename_table("master_products", "product_groups")
