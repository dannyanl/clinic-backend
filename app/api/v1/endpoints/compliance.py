import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import (
    get_current_active_user, require_roles,
)
from app.database.database import get_db
from app.models import (
    DataExportRequest, Patient, PHIAccessLog, PolicyAcceptance,
    PrivacyPolicy, User,
)

router = APIRouter()


# --- Privacy / Terms ---
class PolicyIn(BaseModel):
    kind: str  # privacy | terms | dpa
    version: str
    content: str


class AcceptIn(BaseModel):
    policy_id: int


@router.get("/policies/active")
def active_policies(db: Session = Depends(get_db)):
    rows = db.query(PrivacyPolicy).filter(PrivacyPolicy.active == "true").all()
    return [{"id": r.id, "kind": r.kind, "version": r.version,
             "content": r.content, "effective_at": r.effective_at} for r in rows]


@router.post("/policies", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_policy(payload: PolicyIn, db: Session = Depends(get_db)):
    db.query(PrivacyPolicy).filter(PrivacyPolicy.kind == payload.kind,
                                   PrivacyPolicy.active == "true")\
        .update({PrivacyPolicy.active: "false"})
    obj = PrivacyPolicy(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id}


@router.post("/policies/accept")
def accept_policy(payload: AcceptIn, request: Request,
                  user: User = Depends(get_current_active_user),
                  db: Session = Depends(get_db)):
    pol = db.query(PrivacyPolicy).get(payload.policy_id)
    if not pol:
        raise HTTPException(404, "Not found")
    db.add(PolicyAcceptance(
        user_id=user.id, policy_id=pol.id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    ))
    db.commit()
    return {"detail": "accepted"}


@router.get("/policies/me/pending")
def my_pending_policies(user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    accepted_ids = {a.policy_id for a in
                    db.query(PolicyAcceptance).filter(PolicyAcceptance.user_id == user.id).all()}
    rows = db.query(PrivacyPolicy).filter(PrivacyPolicy.active == "true").all()
    return [{"id": r.id, "kind": r.kind, "version": r.version}
            for r in rows if r.id not in accepted_ids]


# --- PHI access logs ---
@router.get("/phi-access-logs",
            dependencies=[Depends(require_roles("admin"))])
def phi_logs(db: Session = Depends(get_db),
             patient_id: int | None = None, limit: int = 200):
    q = db.query(PHIAccessLog).order_by(PHIAccessLog.created_at.desc())
    if patient_id:
        q = q.filter(PHIAccessLog.patient_id == patient_id)
    rows = q.limit(min(limit, 1000)).all()
    return [{"id": r.id, "user_id": r.user_id, "patient_id": r.patient_id,
             "action": r.action, "resource": r.resource, "resource_id": r.resource_id,
             "purpose": r.purpose, "ip": r.ip, "created_at": r.created_at} for r in rows]


# --- GDPR / Habeas Data ---
class ExportRequestIn(BaseModel):
    kind: str  # export | delete
    notes: str | None = None


@router.post("/me/data-request", status_code=201)
def create_request(payload: ExportRequestIn,
                   user: User = Depends(get_current_active_user),
                   db: Session = Depends(get_db)):
    if payload.kind not in ("export", "delete"):
        raise HTTPException(400, "Invalid kind")
    obj = DataExportRequest(user_id=user.id, kind=payload.kind, notes=payload.notes,
                            tenant_id=user.tenant_id)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "status": obj.status}


@router.get("/me/data-export.json")
def my_data_export(user: User = Depends(get_current_active_user),
                   db: Session = Depends(get_db)):
    """Auto-genera el dump JSON del propio usuario (portabilidad de datos)."""
    from app.models import (
        Appointment, ConsentSignature, MedicalRecord, Payment, Prescription,
    )
    p = db.query(Patient).filter(Patient.user_id == user.id).first()
    payload: dict = {
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "phone": user.phone, "role": user.role, "created_at": user.created_at.isoformat(),
        },
        "patient": None,
        "appointments": [], "medical_records": [], "prescriptions": [],
        "payments": [], "consent_signatures": [],
    }
    if p:
        payload["patient"] = {
            "id": p.id, "dni": p.dni, "birth_date": str(p.birth_date) if p.birth_date else None,
            "blood_type": p.blood_type, "allergies": p.allergies, "notes": p.notes,
        }
        appts = db.query(Appointment).filter(Appointment.patient_id == p.id).all()
        payload["appointments"] = [{
            "id": a.id, "starts_at": a.starts_at.isoformat(), "status": a.status,
            "reason": a.reason, "notes": a.notes,
        } for a in appts]
        recs = db.query(MedicalRecord).filter(MedicalRecord.patient_id == p.id).all()
        payload["medical_records"] = [{
            "id": r.id, "chief_complaint": r.chief_complaint, "diagnosis": r.diagnosis,
            "treatment_plan": r.treatment_plan, "notes": r.notes,
            "created_at": r.created_at.isoformat(),
        } for r in recs]
        rec_ids = [r.id for r in recs]
        if rec_ids:
            rxs = db.query(Prescription).filter(Prescription.record_id.in_(rec_ids)).all()
            payload["prescriptions"] = [{
                "id": rx.id, "drug": rx.drug, "dosage": rx.dosage,
                "frequency": rx.frequency, "duration": rx.duration,
                "instructions": rx.instructions,
            } for rx in rxs]
        pays = db.query(Payment).join(Appointment).filter(Appointment.patient_id == p.id).all()
        payload["payments"] = [{
            "id": pp.id, "amount": float(pp.amount), "currency": pp.currency,
            "status": pp.status, "provider": pp.provider,
            "created_at": pp.created_at.isoformat(),
        } for pp in pays]
        sigs = db.query(ConsentSignature).filter(ConsentSignature.patient_id == p.id).all()
        payload["consent_signatures"] = [{
            "id": s.id, "template_id": s.template_id, "signed_at": s.signed_at.isoformat(),
        } for s in sigs]
    body = json.dumps(payload, indent=2, default=str)
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="my-data-{user.id}.json"'})


@router.get("/data-requests", dependencies=[Depends(require_roles("admin"))])
def list_requests(db: Session = Depends(get_db)):
    rows = db.query(DataExportRequest).order_by(DataExportRequest.created_at.desc()).all()
    return [{"id": r.id, "user_id": r.user_id, "kind": r.kind, "status": r.status,
             "created_at": r.created_at, "resolved_at": r.resolved_at} for r in rows]


@router.post("/data-requests/{rid}/resolve",
             dependencies=[Depends(require_roles("admin"))])
def resolve_request(rid: int, db: Session = Depends(get_db)):
    r = db.query(DataExportRequest).get(rid)
    if not r:
        raise HTTPException(404, "Not found")
    if r.kind == "delete":
        u = db.query(User).get(r.user_id)
        if u:
            u.deleted_at = datetime.now(timezone.utc)
            u.is_active = False
            p = db.query(Patient).filter(Patient.user_id == u.id).first()
            if p:
                p.deleted_at = datetime.now(timezone.utc)
    r.status = "done"
    r.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"detail": "done"}
