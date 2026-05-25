from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"


STAFF_ROLES = {Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST}
