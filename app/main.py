from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1 import api_router
from app.config.settings import settings
from app.core.logging import configure_logging, log
from app.core.rate_limit import limiter
from app.core.sentry import init_sentry
from app.core.startup_checks import run_startup_checks
from app.core import ehr_audit  # noqa: F401  (registers SQLAlchemy event listeners)
from app.database.database import engine, init_db
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.utils.bootstrap import ensure_first_admin


configure_logging()
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_checks()
    init_db()
    ensure_first_admin()
    start_scheduler()
    log.info("app_started", env=settings.ENVIRONMENT, version="5.1.0")
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="5.1.0",
    description="Clinix Health Suite — international multi-tenant clinic management platform",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    db_ok = True
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        import redis as redis_lib  # type: ignore

        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
    except Exception:
        redis_ok = False

    overall = "ok" if (db_ok and redis_ok) else "degraded"
    return {
        "status": overall,
        "database": db_ok,
        "redis": redis_ok,
        "version": "5.1.0",
        "env": settings.ENVIRONMENT,
    }
