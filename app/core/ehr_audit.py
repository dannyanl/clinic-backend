import json

from sqlalchemy import event

from app.models import MedicalRecord, MedicalRecordVersion, Prescription


def _snapshot(rec: MedicalRecord) -> str:
    return json.dumps({
        "patient_id": rec.patient_id,
        "doctor_id": rec.doctor_id,
        "appointment_id": rec.appointment_id,
        "chief_complaint": rec.chief_complaint,
        "diagnosis": rec.diagnosis,
        "treatment_plan": rec.treatment_plan,
        "notes": rec.notes,
        "prescriptions": [
            {"drug": p.drug, "dosage": p.dosage, "frequency": p.frequency,
             "duration": p.duration, "instructions": p.instructions}
            for p in (rec.prescriptions or [])
        ],
    }, default=str)


@event.listens_for(MedicalRecord, "after_insert")
def _after_insert(mapper, connection, target):
    snap = _snapshot(target)
    connection.execute(
        MedicalRecordVersion.__table__.insert(),
        {"record_id": target.id, "snapshot": snap, "action": "create"},
    )


@event.listens_for(MedicalRecord, "after_update")
def _after_update(mapper, connection, target):
    snap = _snapshot(target)
    connection.execute(
        MedicalRecordVersion.__table__.insert(),
        {"record_id": target.id, "snapshot": snap, "action": "update"},
    )


@event.listens_for(MedicalRecord, "after_delete")
def _after_delete(mapper, connection, target):
    snap = _snapshot(target)
    connection.execute(
        MedicalRecordVersion.__table__.insert(),
        {"record_id": target.id, "snapshot": snap, "action": "delete"},
    )
