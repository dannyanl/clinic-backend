from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import SurveyResponse

router = APIRouter()


class AnswerIn(BaseModel):
    nps_score: int = Field(ge=0, le=10)
    comments: str | None = None


@router.get("/{token}")
def open_survey(token: str, db: Session = Depends(get_db)):
    s = db.query(SurveyResponse).filter(SurveyResponse.token == token).first()
    if not s:
        raise HTTPException(404, "Not found")
    return {"id": s.id, "answered": s.answered_at is not None,
            "appointment_id": s.appointment_id}


@router.post("/{token}/answer")
def answer(token: str, payload: AnswerIn, db: Session = Depends(get_db)):
    s = db.query(SurveyResponse).filter(SurveyResponse.token == token).first()
    if not s:
        raise HTTPException(404, "Not found")
    if s.answered_at:
        raise HTTPException(409, "Already answered")
    s.nps_score = payload.nps_score
    s.comments = payload.comments
    s.answered_at = datetime.now(timezone.utc)
    db.commit()
    return {"detail": "Thanks"}


@router.get("/admin/aggregate")
def aggregate(db: Session = Depends(get_db)):
    rows = db.query(SurveyResponse).filter(SurveyResponse.nps_score.isnot(None)).all()
    if not rows:
        return {"responses": 0, "promoters": 0, "passives": 0, "detractors": 0, "nps": 0}
    promoters = sum(1 for r in rows if r.nps_score >= 9)
    detractors = sum(1 for r in rows if r.nps_score <= 6)
    passives = sum(1 for r in rows if 7 <= r.nps_score <= 8)
    n = len(rows)
    nps = round((promoters / n - detractors / n) * 100, 2)
    return {"responses": n, "promoters": promoters, "passives": passives,
            "detractors": detractors, "nps": nps}
