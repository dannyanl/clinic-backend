"""v3 features

Revision ID: 0002_v3_features
Revises: 0001_initial
Create Date: 2026-04-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_v3_features"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New columns on existing tables
    op.add_column("users", sa.Column("is_blocked", sa.Boolean, nullable=False,
                                     server_default=sa.text("false")))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean, nullable=False,
                                     server_default=sa.text("false")))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("patients", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("appointments", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_index("ix_appt_doctor_starts", "appointments", ["doctor_id", "starts_at"])
    op.create_index("ix_appt_patient_starts", "appointments", ["patient_id", "starts_at"])

    # 2FA
    op.create_table(
        "two_factor_secrets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"),
                  unique=True, nullable=False),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("backup_codes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    )

    # Consents
    op.create_table(
        "consent_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.String(8), nullable=False, server_default="active"),
    )
    op.create_table(
        "consent_signatures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("consent_templates.id"),
                  nullable=False),
        sa.Column("patient_id", sa.Integer,
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signed_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("signature_text", sa.String(255), nullable=False),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("snapshot", sa.Text, nullable=False),
    )

    # Inventory
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False, server_default="unit"),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("locations.id")),
        sa.Column("stock", sa.Integer, nullable=False, server_default="0"),
        sa.Column("min_stock", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer,
                  sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(255)),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Templates
    op.create_table(
        "message_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("channel", sa.String(16), nullable=False, server_default="email"),
        sa.Column("subject", sa.String(255)),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("locale", sa.String(8), nullable=False, server_default="es"),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Branding
    op.create_table(
        "branding",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, server_default="Clinic App"),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("primary_color", sa.String(16), nullable=False, server_default="#2563eb"),
        sa.Column("support_email", sa.String(255)),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Surveys (NPS)
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer,
                  sa.ForeignKey("appointments.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("patient_id", sa.Integer,
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nps_score", sa.Integer),
        sa.Column("comments", sa.Text),
        sa.Column("token", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # EHR versioning
    op.create_table(
        "medical_record_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("record_id", sa.Integer,
                  sa.ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edited_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("snapshot", sa.Text, nullable=False),
        sa.Column("action", sa.String(16), nullable=False, server_default="update"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_medical_record_versions_record",
                    "medical_record_versions", ["record_id"])

    # Reminder policies + no-show events
    op.create_table(
        "reminder_policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, server_default="default"),
        sa.Column("hours_before", sa.Integer, nullable=False, server_default="24"),
        sa.Column("channels", sa.String(64), nullable=False, server_default="email"),
        sa.Column("enabled", sa.String(8), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "no_show_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("appointment_id", sa.Integer,
                  sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer,
                  sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_charged", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for t in [
        "no_show_events", "reminder_policies",
        "medical_record_versions", "survey_responses", "branding",
        "message_templates", "inventory_movements", "inventory_items",
        "consent_signatures", "consent_templates", "two_factor_secrets",
    ]:
        op.drop_table(t)
    op.drop_index("ix_appt_patient_starts", table_name="appointments")
    op.drop_index("ix_appt_doctor_starts", table_name="appointments")
    op.drop_column("appointments", "deleted_at")
    op.drop_column("patients", "deleted_at")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "is_blocked")
