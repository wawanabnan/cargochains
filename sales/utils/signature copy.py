# sales/utils/signature.py

from dataclasses import dataclass
from typing import Optional, Any

from sales.models import SalesConfig, SignatureSource


@dataclass(frozen=True)
class SignatureContext:
    user: Optional[Any] = None
    name: str = ""
    title: str = ""
    image: Optional[Any] = None  # ImageField/FileField or None


def _safe_user_name(user) -> str:
    if not user:
        return ""
    full = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    if full:
        return full
    return (getattr(user, "username", "") or "").strip()


def _safe_profile(user):
    return getattr(user, "profile", None) if user else None


def _safe_title(user) -> str:
    p = _safe_profile(user)
    return (getattr(p, "title", "") or "").strip() if p else ""


def _safe_signature_image(user):
    p = _safe_profile(user)
    return getattr(p, "signature", None) if p else None


def _resolve_user_for_quotation(quotation, cfg: SalesConfig):
    if cfg.quotation_signature_source == SignatureSource.SALES_USER:
        return getattr(quotation, "sales_user", None)
    return cfg.quotation_signature_user


def _resolve_user_for_job(job, cfg: SalesConfig):
    if cfg.joborder_signature_source == SignatureSource.SALES_USER:
        return getattr(job, "sales_user", None)
    return cfg.joborder_signature_user


def build_signature_context_for_quotation(quotation) -> dict:
    """
    Return dict siap-tempel ke template:
    signature_user, signature_name, signature_title, signature_image
    """
    cfg = SalesConfig.get_solo()
    user = _resolve_user_for_quotation(quotation, cfg)
    ctx = SignatureContext(
        user=user,
        name=_safe_user_name(user),
        title=_safe_title(user),
        image=_safe_signature_image(user),
    )
    return {
        "signature_user": ctx.user,
        "signature_name": ctx.name,
        "signature_title": ctx.title,
        "signature_image": ctx.image,
    }


def build_signature_context_for_job(job) -> dict:
    cfg = SalesConfig.get_solo()
    user = _resolve_user_for_job(job, cfg)
    ctx = SignatureContext(
        user=user,
        name=_safe_user_name(user),
        title=_safe_title(user),
        image=_safe_signature_image(user),
    )
    return {
        "signature_user": ctx.user,
        "signature_name": ctx.name,
        "signature_title": ctx.title,
        "signature_image": ctx.image,
    }
