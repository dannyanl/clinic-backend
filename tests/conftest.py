import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ──────────────────────────────────────────────────────────────────────────────
# Env defaults — must be set BEFORE any app module is imported
# ──────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("FIRST_ADMIN_EMAIL", "admin@test.local")
os.environ.setdefault("FIRST_ADMIN_PASSWORD", "Admin1234!")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("BACKEND_CORS_ORIGINS", '["http://localhost"]')

# ──────────────────────────────────────────────────────────────────────────────
# Database: prefer DATABASE_URL from the environment (PostgreSQL in CI),
# fall back to an in-memory SQLite for local dev without a running PG.
# ──────────────────────────────────────────────────────────────────────────────
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

if _DATABASE_URL and _DATABASE_URL.startswith("postgresql"):
    # Use the real PostgreSQL database supplied by CI / the dev environment.
    os.environ["DATABASE_URL"] = _DATABASE_URL
    _engine = create_engine(_DATABASE_URL, pool_pre_ping=True)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    _USE_SQLITE = False
else:
    # Fallback: fast in-memory SQLite (no external dependency required).
    _SQLITE_URL = "sqlite:///:memory:"
    os.environ["DATABASE_URL"] = _SQLITE_URL
    _engine = create_engine(
        _SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    _USE_SQLITE = True

from app import database  # noqa: E402  (import after env is fully set)
from app.database.database import Base, get_db  # noqa: E402

# Patch the global engine / session so the app uses our test database
database.engine = _engine
database.SessionLocal = TestingSession


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    Base.metadata.create_all(bind=_engine)

    from app.utils.bootstrap import ensure_first_admin
    ensure_first_admin()

    yield fastapi_app

    # Teardown: drop all tables so the next session starts clean (SQLite only;
    # PostgreSQL CI databases are typically ephemeral anyway).
    if _USE_SQLITE:
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client(app):
    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client):
    r = client.post(
        "/api/v1/auth/login",
        data={
            "username": os.environ["FIRST_ADMIN_EMAIL"],
            "password": os.environ["FIRST_ADMIN_PASSWORD"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
