from fastapi import APIRouter

from .endpoints import (
    tenants, compliance,
    auth, users, doctors, patients, specialties, appointments, reports, admin,
    locations, insurance, ehr, payments, files, waiting_list,
    two_factor, webhooks, search, exports, links, consents, waiting_room,
    inventory, prescriptions_pdf, surveys, calendar, templates, branding,
    trash, policies, prescription_verify,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(two_factor.router, prefix="/auth/2fa", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(specialties.router, prefix="/specialties", tags=["specialties"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(waiting_list.router, prefix="/waiting-list", tags=["waiting-list"])
api_router.include_router(waiting_room.router, prefix="/waiting-room", tags=["waiting-room"])
api_router.include_router(ehr.router, prefix="/medical-records", tags=["medical-records"])
api_router.include_router(prescriptions_pdf.router, prefix="/medical-records", tags=["medical-records"])
api_router.include_router(prescription_verify.router, prefix="/verify-prescription", tags=["public"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["insurance"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(exports.router, prefix="/export", tags=["export"])
api_router.include_router(links.router, prefix="/links", tags=["public"])
api_router.include_router(consents.router, prefix="/consents", tags=["consents"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["surveys"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(templates.router, prefix="/templates", tags=["admin"])
api_router.include_router(branding.router, prefix="/branding", tags=["branding"])
api_router.include_router(trash.router, prefix="/trash", tags=["admin"])
api_router.include_router(policies.router, prefix="/policies", tags=["admin"])
