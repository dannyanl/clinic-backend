"""Plan-based feature enforcement middleware and helpers.

Plans: starter | pro | enterprise
Each plan unlocks a cumulative set of features and resource limits.
"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.models import Tenant

# ── Plan limits ──────────────────────────────────────────────────────────────
PLAN_LIMITS: dict[str, dict] = {
    "starter": {
        "max_doctors": 3,
        "max_patients": 500,
        "max_locations": 1,
        "telemedicine": False,
        "inventory": False,
        "insurance": False,
        "exports": False,
        "webhooks": False,
        "api_access": False,
        "custom_domain": False,
        "branding": False,
        "surveys": False,
        "phi_audit_logs": False,
        "gdpr_tools": False,
        "multi_lang": False,
    },
    "pro": {
        "max_doctors": 20,
        "max_patients": 5000,
        "max_locations": 5,
        "telemedicine": True,
        "inventory": True,
        "insurance": True,
        "exports": True,
        "webhooks": True,
        "api_access": False,
        "custom_domain": True,
        "branding": True,
        "surveys": True,
        "phi_audit_logs": True,
        "gdpr_tools": True,
        "multi_lang": True,
    },
    "enterprise": {
        "max_doctors": 9999,
        "max_patients": 9999999,
        "max_locations": 9999,
        "telemedicine": True,
        "inventory": True,
        "insurance": True,
        "exports": True,
        "webhooks": True,
        "api_access": True,
        "custom_domain": True,
        "branding": True,
        "surveys": True,
        "phi_audit_logs": True,
        "gdpr_tools": True,
        "multi_lang": True,
    },
}

_FEATURE_PLAN_MAP: dict[str, list[str]] = {
    feat: [plan for plan, caps in PLAN_LIMITS.items() if caps.get(feat)]
    for feat in [
        "telemedicine", "inventory", "insurance", "exports", "webhooks",
        "api_access", "custom_domain", "branding", "surveys",
        "phi_audit_logs", "gdpr_tools", "multi_lang",
    ]
}


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


def require_feature(feature: str):
    """FastAPI dependency factory — raises 402 if tenant plan lacks the feature."""
    async def _dependency(request: Request, db: Session = None):
        tenant: Tenant | None = getattr(request.state, "tenant", None)
        if tenant is None:
            return
        limits = get_plan_limits(tenant.plan)
        if not limits.get(feature, False):
            allowed = _FEATURE_PLAN_MAP.get(feature, ["pro", "enterprise"])
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "PLAN_UPGRADE_REQUIRED",
                    "feature": feature,
                    "current_plan": tenant.plan,
                    "available_on": allowed,
                    "message": (
                        f"The '{feature}' feature is not available on the "
                        f"'{tenant.plan}' plan. Upgrade to {' or '.join(allowed)}."
                    ),
                },
            )
    return _dependency


def check_resource_limit(db: Session, tenant: Tenant, resource: str, current_count: int) -> None:
    """Raises 402 if tenant has exceeded a numeric resource limit."""
    limits = get_plan_limits(tenant.plan)
    limit_key = f"max_{resource}"
    max_allowed = limits.get(limit_key)
    if max_allowed is not None and current_count >= max_allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "RESOURCE_LIMIT_REACHED",
                "resource": resource,
                "limit": max_allowed,
                "current": current_count,
                "current_plan": tenant.plan,
                "message": (
                    f"You have reached the {resource} limit ({max_allowed}) "
                    f"for the '{tenant.plan}' plan. Upgrade to increase this limit."
                ),
            },
        )
