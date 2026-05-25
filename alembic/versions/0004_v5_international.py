"""v5 — international readiness: tenant i18n, direct tenant_id on entities, ICD codes

Revision ID: 0004_v5_international
Revises: 0003_v4_tenant_compliance
Create Date: 2026-05-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_v5_international"
down_revision = "0003_v4_tenant_compliance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tenant: i18n + branding + feature flags ───────────────────────────────
    op.add_column("tenants", sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"))
    op.add_column("tenants", sa.Column("default_currency", sa.String(8), nullable=False, server_default="USD"))
    op.add_column("tenants", sa.Column("default_lang", sa.String(8), nullable=False, server_default="en"))
    op.add_column("tenants", sa.Column("branding_logo_url", sa.String(500)))
    op.add_column("tenants", sa.Column("branding_primary_color", sa.String(16)))
    op.add_column("tenants", sa.Column("branding_support_email", sa.String(255)))
    op.add_column("tenants", sa.Column("telemedicine_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("tenants", sa.Column("inventory_enabled", sa.Boolean, nullable=False, server_default="true"))
    op.add_column("tenants", sa.Column("insurance_enabled", sa.Boolean, nullable=False, server_default="true"))

    # ── Patient: direct tenant_id + E.164 phone + preferred lang + country ───
    op.add_column("patients", sa.Column(
        "tenant_id", sa.Integer,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    ))
    op.add_column("patients", sa.Column("phone_e164", sa.String(20)))
    op.add_column("patients", sa.Column("emergency_phone_e164", sa.String(20)))
    op.add_column("patients", sa.Column("country_code", sa.String(2)))
    op.add_column("patients", sa.Column("preferred_lang", sa.String(8)))

    # ── Doctor: direct tenant_id + license_country + currency ────────────────
    op.add_column("doctors", sa.Column(
        "tenant_id", sa.Integer,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    ))
    op.add_column("doctors", sa.Column("license_country", sa.String(2)))
    op.add_column("doctors", sa.Column(
        "consultation_currency", sa.String(8), nullable=False, server_default="USD",
    ))

    # ── Appointment: direct tenant_id + tenant index ──────────────────────────
    op.add_column("appointments", sa.Column(
        "tenant_id", sa.Integer,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    ))
    op.create_index("ix_appt_tenant_starts", "appointments", ["tenant_id", "starts_at"])

    # ── WaitingList: direct tenant_id ─────────────────────────────────────────
    op.add_column("waiting_list", sa.Column(
        "tenant_id", sa.Integer,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True,
    ))

    # ── EHR: ICD-10 / ICD-11 disease codes ──────────────────────────────────
    op.add_column("medical_records", sa.Column("icd10_code", sa.String(16)))
    op.add_column("medical_records", sa.Column("icd11_code", sa.String(16)))

    # ── Payment: default currency from ARS → USD ─────────────────────────────
    # Note: only changes server_default for new rows; existing rows are unchanged
    op.alter_column("payments", "currency",
                    existing_type=sa.String(8),
                    server_default="USD",
                    existing_server_default="ARS")


def downgrade() -> None:
    op.alter_column("payments", "currency",
                    existing_type=sa.String(8),
                    server_default="ARS")

    op.drop_column("medical_records", "icd11_code")
    op.drop_column("medical_records", "icd10_code")

    op.drop_column("waiting_list", "tenant_id")

    op.drop_index("ix_appt_tenant_starts", "appointments")
    op.drop_column("appointments", "tenant_id")

    op.drop_column("doctors", "consultation_currency")
    op.drop_column("doctors", "license_country")
    op.drop_column("doctors", "tenant_id")

    op.drop_column("patients", "preferred_lang")
    op.drop_column("patients", "country_code")
    op.drop_column("patients", "emergency_phone_e164")
    op.drop_column("patients", "phone_e164")
    op.drop_column("patients", "tenant_id")

    for col in [
        "insurance_enabled", "inventory_enabled", "telemedicine_enabled",
        "branding_support_email", "branding_primary_color", "branding_logo_url",
        "default_lang", "default_currency", "timezone",
    ]:
        op.drop_column("tenants", col)
