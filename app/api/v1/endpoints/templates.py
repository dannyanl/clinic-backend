from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import require_roles
from app.database.database import get_db
from app.models import MessageTemplate

router = APIRouter(dependencies=[Depends(require_roles("admin"))])


class TemplateIn(BaseModel):
    code: str
    channel: str = "email"
    subject: str | None = None
    body: str
    locale: str = "es"


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    return [{"id": t.id, "code": t.code, "channel": t.channel, "subject": t.subject,
             "body": t.body, "locale": t.locale, "updated_at": t.updated_at}
            for t in db.query(MessageTemplate).all()]


@router.post("", status_code=201)
def upsert(payload: TemplateIn, db: Session = Depends(get_db)):
    t = db.query(MessageTemplate).filter(MessageTemplate.code == payload.code,
                                         MessageTemplate.locale == payload.locale).first()
    if t:
        for k, v in payload.model_dump().items():
            setattr(t, k, v)
    else:
        t = MessageTemplate(**payload.model_dump()); db.add(t)
    db.commit(); db.refresh(t)
    return {"id": t.id}


@router.delete("/{tid}", status_code=204)
def delete(tid: int, db: Session = Depends(get_db)):
    t = db.query(MessageTemplate).get(tid)
    if not t:
        raise HTTPException(404, "Not found")
    db.delete(t); db.commit()
