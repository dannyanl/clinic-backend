import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config.settings import settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_upload(file: UploadFile, *, subdir: str = "general") -> tuple[str, int]:
    base = Path(settings.UPLOAD_DIR) / subdir
    _ensure_dir(base)
    ext = os.path.splitext(file.filename or "")[1].lower()
    name = f"{uuid4().hex}{ext}"
    target = base / name
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    size = target.stat().st_size
    return str(target), size


def open_for_download(storage_path: str):
    p = Path(storage_path)
    if not p.exists():
        raise FileNotFoundError(storage_path)
    return p
