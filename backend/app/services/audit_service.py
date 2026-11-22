from fastapi import Request
from sqlmodel import Session

from app.models.audit_log import AuditLog


def get_client_meta(request: Request | None) -> tuple[str | None, str | None]:
    if not request:
        return None, None
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    ua = request.headers.get("user-agent", "")[:512] or None
    return ip, ua


def log_event(
    session: Session,
    *,
    user_id: int | None,
    actor_email: str,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    details: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    ip, ua = get_client_meta(request)
    entry = AuditLog(
        user_id=user_id,
        actor_email=actor_email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details[:1000] if details else None,
        ip_address=ip,
        user_agent=ua,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry

