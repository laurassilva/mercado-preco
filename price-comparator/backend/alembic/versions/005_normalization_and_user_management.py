"""Product normalization fields + User management extensions + Access logs

Revision ID: 005
Revises: 004
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MarketProduct parsed columns
    op.add_column("market_products", sa.Column("parsed_brand", sa.String(255), nullable=True))
    op.add_column("market_products", sa.Column("parsed_name", sa.String(500), nullable=True))
    op.add_column("market_products", sa.Column("volume_value", sa.Numeric(10, 3), nullable=True))
    op.add_column("market_products", sa.Column("volume_unit", sa.String(10), nullable=True))
    op.add_column("market_products", sa.Column("volume_base", sa.Numeric(12, 3), nullable=True))
    op.add_column("market_products", sa.Column("volume_base_unit", sa.String(5), nullable=True))
    op.add_column("market_products", sa.Column("product_type", sa.String(50), nullable=True))
    op.add_column("market_products", sa.Column("is_kit", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("market_products", sa.Column("is_combo", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("market_products", sa.Column("pack_quantity", sa.Integer(), nullable=True))
    op.add_column("market_products", sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True))

    # User extended columns
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("position", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("status", sa.String(20), server_default="active", nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("login_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_reset_token", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True))

    # Sync status with is_active for existing users
    op.execute("UPDATE users SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END")

    # Access logs table
    op.create_table(
        "access_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("CREATE INDEX ix_access_logs_user_created ON access_logs (user_id, created_at DESC)")
    op.execute("CREATE INDEX ix_access_logs_created ON access_logs (created_at DESC)")
    op.execute("CREATE INDEX ix_access_logs_action ON access_logs (action, created_at DESC)")


def downgrade() -> None:
    op.drop_table("access_logs")
    for col in ("phone", "company", "position", "status", "last_login_at",
                "must_change_password", "login_attempts", "locked_until",
                "password_reset_token", "password_reset_expires"):
        op.drop_column("users", col)
    for col in ("parsed_brand", "parsed_name", "volume_value", "volume_unit",
                "volume_base", "volume_base_unit", "product_type", "is_kit",
                "is_combo", "pack_quantity", "normalized_at"):
        op.drop_column("market_products", col)
