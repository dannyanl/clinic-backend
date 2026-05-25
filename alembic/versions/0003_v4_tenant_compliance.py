"""v4 multi-tenant + compliance

Revision ID: 0003_v4_tenant_compliance
Revises: 0002_v3_features
Create Date: 2026-04-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_v4_tenant_compliance"
down_revision = "0002_v3_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("custom_domain", sa.String(255), unique=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.add_column("users",
                  sa.Column("tenant_id", sa.Integer,
                            sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True))

    op.create_table(
        "phi_access_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("patient_id", sa.Integer,
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("resource", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.Integer),
        sa.Column("purpose", sa.String(160)),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(),
                  nullable=False, index=True),
    )

    op.create_table(
        "privacy_policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("effective_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("active", sa.String(8), nullable=False, server_default="true"),
    )
    op.create_table(
        "policy_acceptances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("privacy_policies.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("accepted_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "data_export_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text),
        sa.Column("download_token", sa.String(128)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime),
    )


def downgrade() -> None:
    for t in ["data_export_requests", "policy_acceptances",
              "privacy_policies", "phi_access_logs"]:
        op.drop_table(t)
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")
