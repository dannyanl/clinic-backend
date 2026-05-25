from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user, require_roles
from app.database.database import get_db
from app.models import ConsentSignature, ConsentTemplate, Patient, User

router = APIRouter()


class TemplateIn(BaseModel):
    code: str
    title: str
    body: str
    version: int = 1


class SignIn(BaseModel):
    template_id: int
    signature_text: str


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    return [
        {"id": t.id, "code": t.code, "title": t.title, "version": t.version}
        for t in db.query(ConsentTemplate).filter(ConsentTemplate.active == "active").all()
    ]


@router.get("/templates/{tid}")
def get_template(tid: int, db: Session = Depends(get_db)):
    t = db.query(ConsentTemplate).get(tid)
    if not t:
        raise HTTPException(404, "Not found")
    return {"id": t.id, "code": t.code, "title": t.title, "body": t.body, "version": t.version}


@router.post("/templates", status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_template(payload: TemplateIn, db: Session = Depends(get_db)):
    if db.query(ConsentTemplate).filter(ConsentTemplate.code == payload.code).first():
        raise HTTPException(409, "Template exists")
    t = ConsentTemplate(**payload.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id}


@router.post("/sign", status_code=201)
def sign(payload: SignIn, request: Request,
         user: User = Depends(get_current_active_user),
         db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not p:
        raise HTTPException(403, "Patient required")
    t = db.query(ConsentTemplate).get(payload.template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    sig = ConsentSignature(
        template_id=t.id, patient_id=p.id,
        signature_text=payload.signature_text, snapshot=t.body,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(sig); db.commit(); db.refresh(sig)
    return {"id": sig.id, "signed_at": sig.signed_at}


@router.get("/me")
def my_consents(user: User = Depends(get_current_active_user),
                db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not p:
        return []
    sigs = db.query(ConsentSignature).filter(ConsentSignature.patient_id == p.id).all()
    return [{"id": s.id, "template_id": s.template_id, "signed_at": s.signed_at} for s in sigs]
