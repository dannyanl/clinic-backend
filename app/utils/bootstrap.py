from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models import (
    Branding, ConsentTemplate, InsuranceProvider, Location, MessageTemplate,
    PrivacyPolicy, ReminderPolicy, Specialty, Tenant, User,
)


def ensure_first_admin() -> None:
    db: Session = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == settings.DEFAULT_TENANT_SLUG).first()
        if not tenant:
            tenant = Tenant(
                slug=settings.DEFAULT_TENANT_SLUG,
                name=settings.BRAND_NAME or "Clinic Demo",
                plan="enterprise", status="active",
                contact_email=settings.FIRST_ADMIN_EMAIL,
            )
            db.add(tenant); db.flush()

        if not db.query(Specialty).first():
            db.add_all([
                Specialty(name="Clínica Médica", description="Medicina general"),
                Specialty(name="Cardiología", description="Especialista en corazón"),
                Specialty(name="Pediatría", description="Atención de niños"),
                Specialty(name="Dermatología", description="Piel"),
                Specialty(name="Ginecología", description="Salud de la mujer"),
            ])
        if not db.query(Location).first():
            db.add(Location(name="Sede Central", address="Av. Siempre Viva 123",
                            timezone=settings.DEFAULT_TIMEZONE, phone="+54 11 0000-0000"))
        if not db.query(InsuranceProvider).first():
            db.add_all([
                InsuranceProvider(name="OSDE", code="OSDE"),
                InsuranceProvider(name="Swiss Medical", code="SWISS"),
                InsuranceProvider(name="Medicus", code="MEDICUS"),
                InsuranceProvider(name="Particular", code="PART"),
            ])
        if not db.query(Branding).first():
            db.add(Branding(
                name=settings.BRAND_NAME, logo_url=settings.BRAND_LOGO_URL,
                primary_color=settings.BRAND_PRIMARY_COLOR,
                support_email=settings.BRAND_SUPPORT_EMAIL,
            ))
        if not db.query(ReminderPolicy).first():
            db.add_all([
                ReminderPolicy(name="24h", hours_before=24, channels="email", enabled="true"),
                ReminderPolicy(name="2h", hours_before=2, channels="email,sms", enabled="true"),
            ])
        if not db.query(ConsentTemplate).first():
            db.add(ConsentTemplate(
                code="general", title="Consentimiento informado general",
                body=("Declaro haber sido informado/a sobre los procedimientos a realizar, "
                      "sus riesgos, beneficios y alternativas, y consiento la atención médica."),
                version=1, active="active",
            ))
        if not db.query(MessageTemplate).first():
            db.add_all([
                MessageTemplate(code="appt_confirm", channel="email",
                                subject="Confirmación de turno",
                                body="Tu turno con {doctor} el {when} fue confirmado."),
                MessageTemplate(code="appt_reminder", channel="email",
                                subject="Recordatorio de turno",
                                body="Recordá tu turno con {doctor} el {when}."),
                MessageTemplate(code="appt_cancelled", channel="email",
                                subject="Turno cancelado",
                                body="Tu turno con {doctor} el {when} fue cancelado."),
            ])
        if not db.query(PrivacyPolicy).first():
            db.add_all([
                PrivacyPolicy(kind="privacy", version="1.0", active="true",
                              content="Política de privacidad — versión inicial. Editar en el panel admin."),
                PrivacyPolicy(kind="terms", version="1.0", active="true",
                              content="Términos y condiciones — versión inicial. Editar en el panel admin."),
            ])

        admin = db.query(User).filter(User.email == settings.FIRST_ADMIN_EMAIL).first()
        if not admin:
            db.add(User(
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                full_name="Administrador",
                role="admin", is_active=True, email_verified=True,
                tenant_id=tenant.id,
            ))
        elif not admin.tenant_id:
            admin.tenant_id = tenant.id
        # Backfill: cualquier usuario sin tenant cae al default
        for u in db.query(User).filter(User.tenant_id.is_(None)).all():
            u.tenant_id = tenant.id
        db.commit()
    finally:
        db.close()
