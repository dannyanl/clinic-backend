import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user
from app.database.database import get_db
from app.models import User
from app.services import totp_service

router = APIRouter()


class CodePayload(BaseModel):
    code: str


@router.post("/setup")
def setup(user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if user.role == "patient":
        raise HTTPException(403, "2FA is for staff only")
    row, uri = totp_service.setup(db, user)
    import base64
    img = qrcode.make(uri)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return {"otpauth_url": uri, "secret": row.secret, "qr_data_url": qr_data_url}


@router.get("/qr")
def qr(user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    row, uri = totp_service.setup(db, user)
    img = qrcode.make(uri)
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/confirm")
def confirm(payload: CodePayload, user: User = Depends(get_current_active_user),
            db: Session = Depends(get_db)):
    if not totp_service.confirm(db, user, payload.code):
        raise HTTPException(400, "Invalid code")
    return {"detail": "2FA enabled"}


@router.post("/disable")
def disable(payload: CodePayload, user: User = Depends(get_current_active_user),
            db: Session = Depends(get_db)):
    if not totp_service.verify_code(db, user, payload.code):
        raise HTTPException(400, "Invalid code")
    totp_service.disable(db, user)
    return {"detail": "2FA disabled"}
