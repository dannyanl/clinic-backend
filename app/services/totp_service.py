import json
import secrets

import pyotp
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import TwoFactorSecret, User


def setup(db: Session, user: User) -> tuple[TwoFactorSecret, str]:
    secret = pyotp.random_base32()
    backup = [secrets.token_hex(4) for _ in range(8)]
    hashed = [bcrypt.hash(c) for c in backup]
    row = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id).first()
    if row:
        row.secret = secret
        row.enabled = False
        row.backup_codes = json.dumps(hashed)
    else:
        row = TwoFactorSecret(user_id=user.id, secret=secret, enabled=False,
                              backup_codes=json.dumps(hashed))
        db.add(row)
    db.commit(); db.refresh(row)
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email,
                                              issuer_name=settings.TWO_FA_ISSUER)
    return row, uri  # also returns provisioning URI; backup codes returned separately


def confirm(db: Session, user: User, code: str) -> bool:
    row = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id).first()
    if not row:
        return False
    if not pyotp.TOTP(row.secret).verify(code, valid_window=1):
        return False
    row.enabled = True
    user.two_factor_enabled = True
    db.commit()
    return True


def verify_code(db: Session, user: User, code: str) -> bool:
    row = db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id,
                                           TwoFactorSecret.enabled.is_(True)).first()
    if not row:
        return True  # 2FA not active
    if pyotp.TOTP(row.secret).verify(code, valid_window=1):
        return True
    # try backup codes
    try:
        codes = json.loads(row.backup_codes or "[]")
    except Exception:
        codes = []
    for i, hashed in enumerate(codes):
        if bcrypt.verify(code, hashed):
            codes.pop(i)
            row.backup_codes = json.dumps(codes)
            db.commit()
            return True
    return False


def disable(db: Session, user: User) -> None:
    db.query(TwoFactorSecret).filter(TwoFactorSecret.user_id == user.id).delete()
    user.two_factor_enabled = False
    db.commit()


def issue_plain_backup_codes() -> list[str]:
    return [secrets.token_hex(4) for _ in range(8)]
